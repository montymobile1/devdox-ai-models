# Repository Pattern – Implementation & Contribution Guide

This document explains how to **create new repositories**, **add functions to existing repositories**, and **write test doubles** in the `models_src` package.  

---

## 1. Project Structure

```
root/
  models_src/
    models/                # ORM-specific models (Tortoise ORM)
    dto/                   # DTOs (Request/Response dataclasses)
    repositories/          # Repository interfaces + implementations
    test_doubles/
      repositories/        # Fakes & Stubs for repositories
```

---

## 2. Core Concepts

The Purpose of the Repository Pattern/Layer:
- **Abstracts** database logic from the rest of the application.
- **Prevents ORM model leakage** by returning DTOs instead of raw ORM objects.
- **Ensures consistency** via naming conventions and strict `Protocol` interfaces.
- **Supports multiple implementations** (e.g., Tortoise ORM, in-memory fakes, stubs).

---

## 3. Models Layer

**Location:** `models_src/models/`

- Define ORM-specific models (Tortoise ORM in this project).
- Contain only persistence-related logic (fields, constraints, Meta, `__str__`, etc.).
- **Never** include business logic or service orchestration.

**Example:**
```python
class APIKEY(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = fields.CharField(max_length=255, null=False)
    api_key = fields.CharField(max_length=512, null=False)
    ...
```

---

## 4. DTO Layer

**Location:** `models_src/dto/`

- Act as **liaison models** between ORM models and business logic.
- Prevent ORM objects from leaking into the main code.
- Provide **typed, structured** request/response data.

**Example:**
```python
@dataclass
class APIKeyResponseDTO:
    id: uuid.UUID
    user_id: str
    masked_api_key: str
    ...
```

---

## 5. Repository Layer

**Location:** `models_src/repositories/`

### Structure
Each repository module contains:
1. **Interface** (Protocol) — defines available operations.
2. **Concrete implementation** — implements the interface using a specific ORM.

**Example:**
```python
class IApiKeyStore(Protocol):
    async def save(self, create_model: APIKeyRequestDTO) -> APIKeyResponseDTO: ...
    async def find_all_by_user_id(...) -> List[APIKeyResponseDTO]: ...
    ...

class TortoiseApiKeyStore(IApiKeyStore):
    model = APIKEY
    model_mapper = TortoiseModelMapper
    ...
```

---

## 6. Naming Conventions

Pattern:
```
<operation_name>_<object_effected>_by_<field_names>_<AND|OR>_<field_names>
```

### Operation Names
- **`get`** → strict retrieval. Must return a value or raise an exception.
- **`find`** → non-strict retrieval. May return an empty result instead of raising.
- **`save`** → insert or update.
- **`update`** → partial or full updates.
- **`delete`** → remove data.

### Object Affected
- `first`, `all`, or a specific field name.
- Example: `find_all_by_user_id`
- Example: `get_first_by_email_and_is_active`

---

## 7. Adding a New Repository

### Step 1 — Define the Interface
- Create a `Protocol` class in `models_src/repositories/`.
- Fully type all parameters and return values.
- Include docstrings explaining behavior.

### Step 2 — Implement the Interface
- Create a concrete implementation for your ORM.
- Use `TortoiseModelMapper` for model → DTO conversion.
- Follow **naming conventions** and **validation patterns**.
- Use `find` for optional results, `get` for required ones.

### Step 3 — Return DTOs Only
- Never return ORM model instances.
- Use `.map_model_to_dataclass()` and `.map_models_to_dataclasses_list()`.

### Step 4 — Test Coverage
- Write **unit tests** against the interface.
- Create **Fakes** and **Stubs** (see section 8).

---

## 8. Test Doubles

**Location:** `models_src/test_doubles/repositories/`

Purpose:
- Allow tests to run without a real DB.
- Keep tests fast, deterministic, and isolated.

### Types
#### 8.1 Fakes
- Implement the repository interface.
- Store data **in-memory**.
- Behave like a real repository.
- For functional and integration tests.

#### 8.2 Stubs
- Implement the repository interface.
- Return predefined responses.
- No actual data operations.
- For unit tests that care only about return values.

---

### 8.3 Base Classes for Test Doubles (`bases.py`)

All test doubles inherit from these base classes for consistency.

**Usage:**
- **Fakes** → extend `FakeBase`, keep in-memory store, call `_before()` in each method to track calls & raise planned exceptions.
- **Stubs** → extend `StubPlanMixin`, use `set_output()` in tests to predefine return values, and `_stub()` in method bodies.

---

## 9. General Rules & Best Practices
- Always define an interface (`Protocol`) before implementing.
- Never let ORM objects leak into calling code.
- Validate inputs before executing DB operations.
- Use `find` for optional results, `get` for required ones.
- All test doubles must implement the same interface as real repositories.
- Use base classes from `bases.py` for consistent spying, stubbing, and exception planning.

---
