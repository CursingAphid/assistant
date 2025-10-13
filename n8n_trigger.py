#!/usr/bin/env python3
"""
n8n Workflow Trigger Examples
This script demonstrates different ways to trigger n8n workflows from Python.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

class N8nWorkflowTrigger:
    def __init__(self, n8n_base_url: str = "http://localhost:5678"):
        """
        Initialize the n8n workflow trigger.
        
        Args:
            n8n_base_url: Base URL of your n8n instance
        """
        self.base_url = n8n_base_url.rstrip('/')
        self.session = requests.Session()
        
    def trigger_webhook_workflow(self, webhook_path: str, data: Dict[Any, Any]) -> Dict[str, Any]:
        """
        Trigger a workflow via webhook.
        
        Args:
            webhook_path: The webhook path (e.g., 'webhook/my-workflow')
            data: Data to send to the workflow
            
        Returns:
            Response from n8n
        """
        webhook_url = f"{self.base_url}/webhook/{webhook_path}"
        
        try:
            response = self.session.post(
                webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.content else None
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def trigger_workflow_by_id(self, workflow_id: str, data: Optional[Dict[Any, Any]] = None) -> Dict[str, Any]:
        """
        Trigger a workflow by its ID using n8n API.
        
        Args:
            workflow_id: The ID of the workflow to trigger
            data: Optional data to pass to the workflow
            
        Returns:
            Response from n8n
        """
        api_url = f"{self.base_url}/api/v1/workflows/{workflow_id}/execute"
        
        payload = {}
        if data:
            payload['data'] = data
            
        try:
            response = self.session.post(
                api_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.content else None
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_workflows(self) -> Dict[str, Any]:
        """
        Get list of all workflows.
        
        Returns:
            List of workflows
        """
        api_url = f"{self.base_url}/api/v1/workflows"
        
        try:
            response = self.session.get(api_url)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_workflow_executions(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get executions for a specific workflow.
        
        Args:
            workflow_id: The ID of the workflow
            
        Returns:
            List of executions
        """
        api_url = f"{self.base_url}/api/v1/executions"
        params = {'workflowId': workflow_id}
        
        try:
            response = self.session.get(api_url, params=params)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """
    Example usage of the N8nWorkflowTrigger class.
    """
    # Initialize the trigger
    n8n = N8nWorkflowTrigger()
    
    print("🚀 n8n Workflow Trigger Examples")
    print("=" * 50)
    
    # Example 1: Trigger via webhook
    print("\n1. Triggering workflow via webhook...")
    webhook_data = {
        "message": "Hello from Python!",
        "timestamp": time.time(),
        "user": "python_script",
        "data": {
            "temperature": 25.5,
            "humidity": 60,
            "location": "San Francisco"
        }
    }
    
    # Note: Replace 'sample-workflow' with your actual webhook path
    result = n8n.trigger_webhook_workflow("sample-workflow", webhook_data)
    print(f"Webhook result: {json.dumps(result, indent=2)}")
    
    # Example 2: Get all workflows
    print("\n2. Getting all workflows...")
    workflows = n8n.get_workflows()
    if workflows['success']:
        print(f"Found {len(workflows['data']['data'])} workflows:")
        for workflow in workflows['data']['data']:
            print(f"  - {workflow['name']} (ID: {workflow['id']})")
    else:
        print(f"Error getting workflows: {workflows['error']}")
    
    # Example 3: Trigger workflow by ID (if you have workflows)
    print("\n3. Triggering workflow by ID...")
    # Replace with actual workflow ID from step 2
    workflow_id = "1"  # Example ID
    trigger_data = {
        "input": "This is triggered from Python",
        "parameters": {
            "delay": 5,
            "retry_count": 3
        }
    }
    
    result = n8n.trigger_workflow_by_id(workflow_id, trigger_data)
    print(f"Workflow trigger result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
