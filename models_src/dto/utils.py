from dataclasses import asdict, fields
from typing import List, Optional, Type

from tortoise import Model


class DataclassMapper:

    @staticmethod
    def map_dataclass_to_dataclass[target_type](
        source, target_cls: Type[target_type], source_target_mapping=None
    ) -> Optional[target_type]:

        if not source or not target_cls:
            return None

        if source_target_mapping is None:
            source_target_mapping = {}

        source_dict = asdict(source)

        if source_target_mapping:
            for old_key, new_key in source_target_mapping.items():
                source_dict[new_key] = source_dict.pop(old_key)

        return target_cls(**source_dict)


class TortoiseModelMapper:

    @staticmethod
    def map_model_to_dataclass[target_type](
        source: Model, target_cls: Type[target_type]
    ) -> Optional[target_type]:
        if not source or not target_cls:
            return None

        # Only grab actual model fields, not internal attributes
        raw_data = {
            field: getattr(source, field) for field in source._meta.fields_map.keys()
        }

        # Match dataclass fields
        target_fields = {f.name for f in fields(target_cls)}
        filtered_data = {k: v for k, v in raw_data.items() if k in target_fields}
        return target_cls(**filtered_data)

    @staticmethod
    def map_models_to_dataclasses_list[target_type](
        sources: List[Model], target_cls: Type[target_type]
    ) -> List[target_type]:
        if not sources or not target_cls:
            return []

        # Pre-fetch model field names ONCE
        model_field_names = sources[0]._meta.fields_map.keys()
        dataclass_field_names = {f.name for f in fields(target_cls)}
        intersect_fields = model_field_names & dataclass_field_names

        # Bulk extract raw dicts
        raw_dicts = [
            {field: getattr(obj, field) for field in intersect_fields}
            for obj in sources
        ]

        # Bulk construct dataclasses
        return [target_cls(**d) for d in raw_dicts]
