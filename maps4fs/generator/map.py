"""This module contains Map class, which is used to generate map using all components."""

from __future__ import annotations

import os
import shutil
from typing import Any, Generator

from maps4fs.generator.component import Component
from maps4fs.generator.game import Game
from maps4fs.logger import Logger


# pylint: disable=R0913, R0902
class Map:
    """Class used to generate map using all components.

    Arguments:
        game (Type[Game]): Game for which the map is generated.
        coordinates (tuple[float, float]): Coordinates of the center of the map.
        size (int): Height and width of the map in pixels (it's a square).
        map_directory (str): Path to the directory where map files will be stored.
        logger (Any): Logger instance
    """

    def __init__(  # pylint: disable=R0917
        self,
        game: Game,
        coordinates: tuple[float, float],
        size: int,
        rotation: int,
        map_directory: str,
        logger: Any = None,
        **kwargs,
    ):
        if not logger:
            logger = Logger(to_stdout=True, to_file=False)
        self.logger = logger
        self.size = size

        if rotation:
            rotation_multiplier = 1.5
        else:
            rotation_multiplier = 1

        self.rotation = rotation
        self.rotated_size = int(size * rotation_multiplier)

        self.game = game
        self.components: list[Component] = []
        self.coordinates = coordinates
        self.map_directory = map_directory

        self.logger.info("Game was set to %s", game.code)

        self.kwargs = kwargs
        self.logger.info("Additional arguments: %s", kwargs)

        os.makedirs(self.map_directory, exist_ok=True)
        self.logger.debug("Map directory created: %s", self.map_directory)

        try:
            shutil.unpack_archive(game.template_path, self.map_directory)
            self.logger.debug("Map template unpacked to %s", self.map_directory)
        except Exception as e:
            raise RuntimeError(f"Can not unpack map template due to error: {e}") from e

    def generate(self) -> Generator[str, None, None]:
        """Launch map generation using all components. Yield component names during the process.

        Yields:
            Generator[str, None, None]: Component names.
        """
        for game_component in self.game.components:
            component = game_component(
                self.game,
                self,
                self.coordinates,
                self.size,
                self.rotated_size,
                self.rotation,
                self.map_directory,
                self.logger,
                **self.kwargs,
            )
            self.components.append(component)

            yield component.__class__.__name__

            try:
                component.process()
            except Exception as e:  # pylint: disable=W0718
                self.logger.error(
                    "Error processing component %s: %s",
                    component.__class__.__name__,
                    e,
                )
                raise e

            try:
                component.commit_generation_info()
            except Exception as e:  # pylint: disable=W0718
                self.logger.error(
                    "Error committing generation info for component %s: %s",
                    component.__class__.__name__,
                    e,
                )
                raise e

    def get_component(self, component_name: str) -> Component | None:
        """Get component by name.

        Arguments:
            component_name (str): Name of the component.

        Returns:
            Component | None: Component instance or None if not found.
        """
        for component in self.components:
            if component.__class__.__name__ == component_name:
                return component
        return None

    def previews(self) -> list[str]:
        """Get list of preview images.

        Returns:
            list[str]: List of preview images.
        """
        previews = []
        for component in self.components:
            try:
                previews.extend(component.previews())
            except Exception as e:  # pylint: disable=W0718
                self.logger.error(
                    "Error getting previews for component %s: %s",
                    component.__class__.__name__,
                    e,
                )
        return previews

    def pack(self, archive_path: str, remove_source: bool = True) -> str:
        """Pack map directory to zip archive.

        Arguments:
            archive_path (str): Path to the archive.
            remove_source (bool, optional): Remove source directory after packing.

        Returns:
            str: Path to the archive.
        """
        archive_path = shutil.make_archive(archive_path, "zip", self.map_directory)
        self.logger.info("Map packed to %s.zip", archive_path)
        if remove_source:
            try:
                shutil.rmtree(self.map_directory)
                self.logger.info("Map directory removed: %s", self.map_directory)
            except Exception as e:  # pylint: disable=W0718
                self.logger.error("Error removing map directory %s: %s", self.map_directory, e)
        return archive_path
