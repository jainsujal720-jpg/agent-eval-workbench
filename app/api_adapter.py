"""HTTP adapter: expectations stay in the evaluator, never sent to chatbot."""
import json
import os
from urllib.request import Request, urlopen

class APISession:
    def __init__(self, customer_id, provider='staging'):
        self.customer_id = customer_id
        self.session_id = None
    def turn(self, text, fault='none'):
        data = dict(customer_id=self.customer_id, message=text, session_id=self.session_id, fault=fault)
        request = Request('http://127.0.0.1:8010/chat', data=json.dumps(data).encode(),
            headers={'Content-Type':'application/json', 'Authorization':'Bearer '+os.getenv('AGENTEVAL_STAGING_TOKEN','local-demo-token')})
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        if not isinstance(result, dict) or not isinstance(result.get('answer'), str):
            raise ValueError('Invalid chatbot response')
        self.session_id = result.pop('session_id')
        return result
