# Lambda Cost Reporting System

A serverless AWS cost reporting system that automatically generates and emails cost reports for multiple clients.

## Project Structure

```
lambda-cost-reporting-system/
├── src/                    # Source code
│   ├── handlers/          # Lambda handlers
│   ├── services/          # Business logic services
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── tests/                 # Test files
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── infrastructure/       # AWS CDK infrastructure code
├── docs/                 # Documentation
├── requirements.txt      # Python dependencies
└── pytest.ini           # Test configuration
```

## Development Setup

1. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements-dev.txt
```

3. Run tests:
```bash
pytest
```

## Infrastructure

The system uses AWS CDK for infrastructure as code. See `infrastructure/` directory for deployment instructions.

## Requirements

- Python 3.9+
- AWS CLI configured
- Node.js 18+ (for CDK)