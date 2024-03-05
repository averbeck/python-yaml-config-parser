from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


class ExtendedConfigInterface(ABC):
    @abstractmethod
    def load_config(self, allow_empty: bool = True):
        raise NotImplementedError

    @abstractmethod
    def ensure_entry(self, key: str, value: str | None = None):
        raise NotImplementedError

    @abstractmethod
    def set_entry(self, key: str, value: str | None = None):
        raise NotImplementedError

    @abstractmethod
    def get_entry(self, key: str):
        raise NotImplementedError

    @abstractmethod
    def get_section(self, section):
        raise NotImplementedError


class YamlConfig(ExtendedConfigInterface):
    def __init__(self, config_file: Path | None = None, allow_empty: bool = True, parent: Any | None = None):
        self.config_file: Path = config_file if config_file else Path("config.yaml")
        self._needs_rewrite: bool = False
        self.content = {}

        self.parent: "YamlConfig | None" = parent
        if not parent:
            self.load_config(allow_empty)

    def __repr__(self) -> str:
        return "YamlConfig: " + str(self.as_dict())

    def __getitem__(self, key) -> Any:
        return self.content[key]

    def __setitem__(self, key, value) -> None:
        self.set_entry(key, value)

    def as_dict(self) -> dict:
        dictionary = {}
        for key, value in self.content.items():
            if isinstance(value, YamlConfig):
                dictionary[key] = value.as_dict()
            else:
                dictionary[key] = value
        return dictionary

    def load_config(self, allow_empty: bool = True) -> None:
        try:
            with self.config_file.open("r", encoding="utf-8") as file_pointer:
                content = yaml.safe_load(file_pointer)
        except FileNotFoundError as err:
            if not allow_empty:
                raise err
            content = {}

        if not isinstance(content, dict):
            if not allow_empty:
                raise TypeError("Configuration file was empty")
            else:
                content = {}

        for key, value in content.items():
            if isinstance(value, dict):
                self.add_section(key, value)
            else:
                self.set_entry(key, value)

    def save_config(self, config_file: Path | None = None) -> None:
        if self.parent:
            self.parent._needs_rewrite |= self._needs_rewrite
            self.parent.save_config(config_file)
            return

        if not self.needs_rewrite():
            return

        if config_file is None:
            config_file = self.config_file

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with config_file.open("w", encoding="utf-8") as file_pointer:
            yaml.representer.SafeRepresenter.add_representer(YamlConfig, yaml_config_serializer)
            yaml.safe_dump(self, file_pointer, indent=4)

    def needs_rewrite(self) -> bool:
        for value in self.content.values():
            if isinstance(value, YamlConfig):
                self._needs_rewrite |= value.needs_rewrite()
        return self._needs_rewrite

    def get_entry(self, key: str) -> Any:
        return self.content[key]

    def ensure_entry(self, key: str, value: str | None = None) -> None:
        if key not in self.content:
            self.set_entry(key, value)

    def set_entry(self, key: str, value: str | None = None) -> None:
        if isinstance(value, dict):
            self.add_section(key, value)
            return

        self.content[key] = value
        self._needs_rewrite = True

    def add_section(self, section: str, content: dict | None = None) -> "YamlConfig":
        if section not in self.content:
            config_section = YamlConfig(parent=self)
        else:
            config_section = self.content[section]

        content = {} if not content else content

        for key, value in content.items():
            if isinstance(value, dict):
                config_section.add_section(key, value)
            else:
                config_section.set_entry(key, value)

        self.content[section] = config_section
        return config_section

    def get_section(self, section: str):
        return self.content[section]


def yaml_config_serializer(dumper, data: YamlConfig):
    dict_rep: dict = data.as_dict()
    node = dumper.represent_dict(dict_rep)
    return node
