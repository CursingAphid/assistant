# Assistant - n8n Workflow Automation

This repository contains an n8n installation for workflow automation and AI assistant capabilities, with Python integration examples.

## Getting Started

### Prerequisites
- Node.js (v18 or higher)
- npm
- Python 3.7+

### Installation
The project dependencies are already installed. To start n8n:

```bash
npm start
```

This will start the n8n server, typically accessible at `http://localhost:5678`.

### Python Integration

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### Triggering Workflows from Python

There are several ways to trigger n8n workflows from Python:

##### 1. Webhook Method (Recommended)
The simplest way is to use webhooks. Create a workflow in n8n with a Webhook trigger node, then use Python to send data to it.

```python
import requests
import json

# Send data to n8n webhook
webhook_url = "http://localhost:5678/webhook/your-webhook-path"
data = {"message": "Hello from Python!", "value": 42}

response = requests.post(webhook_url, json=data)
print(response.json())
```

##### 2. Using the Provided Scripts

**Simple Trigger (`simple_trigger.py`):**
```bash
python simple_trigger.py
```

**Advanced Trigger (`n8n_trigger.py`):**
```bash
python n8n_trigger.py
```

##### 3. Sample Workflow
Import the `sample_workflow.json` into n8n to test the Python integration:
1. Open n8n at `http://localhost:5678`
2. Click "Import from file"
3. Select `sample_workflow.json`
4. Activate the workflow
5. Run `python simple_trigger.py` to test

### Workflow Creation Steps

1. **Start n8n server** with `npm start`
2. **Open n8n interface** at `http://localhost:5678`
3. **Create a new workflow**:
   - Add a "Webhook" node as the trigger
   - Configure the webhook path (e.g., "python-trigger")
   - Add processing nodes (Set, HTTP Request, etc.)
   - Add a "Respond to Webhook" node to return data
4. **Activate the workflow**
5. **Test with Python** using the provided scripts

### API Methods

The `n8n_trigger.py` script provides several methods:

- `trigger_webhook_workflow()` - Trigger via webhook
- `trigger_workflow_by_id()` - Trigger by workflow ID
- `get_workflows()` - List all workflows
- `get_workflow_executions()` - Get execution history

### Example Use Cases

- **Data Processing**: Send data from Python scripts to n8n for processing
- **Scheduled Tasks**: Trigger workflows from Python cron jobs
- **API Integration**: Use n8n as a middleware between Python and external APIs
- **Automation**: Trigger complex workflows from simple Python scripts

### Features
- Workflow automation
- AI-powered assistant capabilities
- Integration with various services and APIs
- Visual workflow builder
- Python integration examples
- Webhook triggers
- REST API access

## License
ISC
