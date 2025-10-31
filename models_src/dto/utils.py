from dataclasses import asdict, fields, is_dataclass
from typing import List, Optional, Type, Any, TypeVar

from tortoise import Model

target_type = TypeVar("target_type")

class DataclassMapper:

    @staticmethod
    def map_models_to_dataclasses_list(
            sources: List[Any], target_cls: Type[target_type]
    ) -> List[target_type]:
        if not sources or not target_cls or not is_dataclass(target_cls):
            return []

        dataclass_field_names = {f.name for f in fields(target_cls)}
        results = []

        for obj in sources:
            # Beanie documents support .dict() or .model_dump()
            raw_dict = obj.dict() if hasattr(obj, "dict") else obj.__dict__

            # Keep only the fields existing in the dataclass
            filtered_dict = {
                key: value for key, value in raw_dict.items()
                if key in dataclass_field_names
            }

            results.append(target_cls(**filtered_dict))

        return results

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
    def map_models_to_dataclasses_list(
            sources: List[Any],
            target_cls: Type[target_type]
    ) -> List[target_type]:
        if not sources or not target_cls:
            return []


        # Beanie documents support .dict() or .model_dump()
        first_obj = sources[0]
        sample_dict = (
            first_obj.dict() if hasattr(first_obj, "dict") else first_obj.__dict__
        )

        model_field_names = set(sample_dict.keys())
        dataclass_field_names = {f.name for f in fields(target_cls)}
        intersect_fields = model_field_names & dataclass_field_names

        # Bulk extract raw dicts
        raw_dicts = [
            {field: getattr(obj, field, None) for field in intersect_fields}
            for obj in sources
        ]

        # Bulk construct dataclasses
        return [target_cls(**d) for d in raw_dicts]
