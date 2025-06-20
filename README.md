# DevDox AI Models

A shared Python package containing Tortoise ORM models and database utilities for microservices architecture. Built for modern async Python applications with FastAPI integration and Supabase support.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tortoise ORM](https://img.shields.io/badge/tortoise--orm-0.20+-green.svg)](https://tortoise.github.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-compatible-orange.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Shared Models**: Common database models (User, Product, Order) for microservices
- **Database Utilities**: Easy configuration for PostgreSQL, MySQL, SQLite, and Supabase
- **FastAPI Integration**: Seamless integration with FastAPI lifespan management
- **Migration Support**: Compatible with Aerich for database migrations
- **Type Safety**: Full type hints and Pydantic schema support
- **Modern Standards**: Built with Python 3.12+ and async/await patterns

## Installation

### Basic Installation

```bash
pip install tortoise-models
```

### Database-Specific Installation

```bash
# PostgreSQL (recommended for production)
pip install tortoise-models[postgresql]


# All database drivers
pip install tortoise-models[all]

# Development dependencies
pip install tortoise-models[dev]
```

## Quick Start

### 1. Basic Setup

```python
from tortoise_models import get_tortoise_config, DatabaseConfig, init_tortoise, close_tortoise
from tortoise_models.models import User, Product, Order

# Configure database
db_config = DatabaseConfig.postgres_config(
    host="localhost",
    port=5432,
    user="postgres",
    password="password",
    database="mydb"
)

# Get Tortoise configuration
tortoise_config = get_tortoise_config(db_config)

# Initialize
await init_tortoise(tortoise_config)

# Use models
user = await User.create(
    username="john_doe",
    email="john@example.com",
    password_hash="hashed_password"
)

# Clean up
await close_tortoise()
```

### Code Quality

```bash
# Format code
black devdox-ai-models/
isort devdox-ai-models/

# Type checking
mypy devdox-ai-models/

# Linting
flake8 devdox-ai-models/

# Run all quality checks
pre-commit run --all-files
```

### Building and Publishing

```bash
# Build the package
python -m build

# Check the build
twine check dist/*

# Upload to PyPI
twine upload dist/*
```


### Performance Tips

1. **Connection Pooling**: Configure appropriate `min_connections` and `max_connections`
2. **Indexes**: The models include optimized indexes for common queries
3. **Prefetch**: Use `prefetch_related()` for foreign key relationships
4. **Select Related**: Use `select_related()` for one-to-one relationships

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v0.1.0 (Initial Release)

- Basic models (User, Product, Order)
- Database configuration utilities
- FastAPI integration
- Supabase support
- Migration compatibility
- Full type hints
- Comprehensive test suite

## Support

- **Documentation**: [GitHub README](https://github.com/yourusername/tortoise-models#readme)
- **Issues**: [GitHub Issues](https://github.com/yourusername/tortoise-models/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tortoise-models/discussions)

## Related Projects

- [Tortoise ORM](https://tortoise.github.io/) - The underlying ORM
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation library
- [Aerich](https://github.com/tortoise/aerich) - Database migration tool