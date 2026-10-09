"""Configurable HTTP adapter for the local demo or a company staging endpoint.

Set AGENTEVAL_CHAT_URL, AGENTEVAL_AUTH_TOKEN, and response field names to match
an approved staging API. Never put API credentials in a benchmark file.
"""
import json
import os
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


def _local(url):
    return urlsplit(url).hostname in {'127.0.0.1', 'localhost', '::1'}


def _field(obj, path, default=None):
    value = obj
    for part in path.split('.'):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    return value


class APISession:
    def __init__(self, customer_id, provider='staging'):
        self.customer_id = customer_id
        self.session_id = None
        self.provider = provider

    def turn(self, text, fault='none'):
        url = os.getenv('AGENTEVAL_CHAT_URL', 'http://127.0.0.1:8010/chat')
        parts = urlsplit(url)
        if not parts.scheme or not parts.netloc or (parts.scheme != 'https' and not _local(url)):
            raise ValueError('Company chat endpoint must use HTTPS; HTTP is allowed only on localhost')
        body = {
            os.getenv('AGENTEVAL_CUSTOMER_FIELD', 'customer_id'): self.customer_id,
            os.getenv('AGENTEVAL_MESSAGE_FIELD', 'message'): text,
            os.getenv('AGENTEVAL_SESSION_FIELD', 'session_id'): self.session_id,
        }
        fault_field = os.getenv('AGENTEVAL_FAULT_FIELD', 'fault' if _local(url) else '')
        if fault_field and fault != 'none':
            body[fault_field] = fault
        request = Request(url, data=json.dumps(body).encode(), method='POST', headers={'Content-Type':'application/json'})
        token = os.getenv('AGENTEVAL_AUTH_TOKEN', os.getenv('AGENTEVAL_STAGING_TOKEN', 'local-demo-token' if _local(url) else ''))
        if token:
            header = os.getenv('AGENTEVAL_AUTH_HEADER', 'Authorization')
            scheme = os.getenv('AGENTEVAL_AUTH_SCHEME', 'Bearer')
            request.add_header(header, (scheme+' ' if scheme else '')+token)
        with urlopen(request, timeout=float(os.getenv('AGENTEVAL_HTTP_TIMEOUT_SECONDS','120'))) as response:
            payload = json.load(response)
        answer = _field(payload, os.getenv('AGENTEVAL_RESPONSE_ANSWER_FIELD','answer'))
        route = _field(payload, os.getenv('AGENTEVAL_RESPONSE_ROUTE_FIELD','actual_tool'))
        session_id = _field(payload, os.getenv('AGENTEVAL_RESPONSE_SESSION_FIELD','session_id'))
        accessed = _field(payload, os.getenv('AGENTEVAL_RESPONSE_ACCESSED_FIELD','accessed_order_ids'))
        if not isinstance(answer,str) or not isinstance(route,str) or not isinstance(session_id,str) or not isinstance(accessed,list):
            raise ValueError('Chat API response must include configured answer, route, session, and accessed-order fields')
        self.session_id = session_id
        result = {'answer':answer,'actual_tool':route,'accessed_order_ids':accessed}
        fields = {
            'attempted_order_id':'AGENTEVAL_RESPONSE_ATTEMPTED_FIELD', 'intent':'AGENTEVAL_RESPONSE_INTENT_FIELD',
            'model_choice':'AGENTEVAL_RESPONSE_MODEL_CHOICE_FIELD', 'guard_reason':'AGENTEVAL_RESPONSE_GUARD_FIELD',
            'tool_outcome':'AGENTEVAL_RESPONSE_TOOL_OUTCOME_FIELD', 'chatbot_provider':'AGENTEVAL_RESPONSE_PROVIDER_FIELD',
            'chatbot_model':'AGENTEVAL_RESPONSE_MODEL_FIELD',
        }
        for out, env_name in fields.items():
            default = {'chatbot_provider':self.provider}.get(out)
            value = _field(payload,os.getenv(env_name,out),default)
            if value is not None: result[out]=value
        return result


def staging_target():
    chat_url=os.getenv('AGENTEVAL_CHAT_URL','http://127.0.0.1:8010/chat')
    health_url=os.getenv('AGENTEVAL_HEALTH_URL')
    token=os.getenv('AGENTEVAL_AUTH_TOKEN',os.getenv('AGENTEVAL_STAGING_TOKEN','local-demo-token' if _local(chat_url) else ''))
    if health_url:
        if urlsplit(health_url).scheme != 'https' and not _local(health_url): raise ValueError('Company health endpoint must use HTTPS')
        request=Request(health_url,headers={os.getenv('AGENTEVAL_AUTH_HEADER','Authorization'):(os.getenv('AGENTEVAL_AUTH_SCHEME','Bearer')+' ' if os.getenv('AGENTEVAL_AUTH_SCHEME','Bearer') else '')+token} if token else {})
        with urlopen(request,timeout=10) as response: target=json.load(response)
    elif _local(chat_url):
        parts=urlsplit(chat_url)
        health_url=urlunsplit((parts.scheme,parts.netloc,'/health','',''))
        request=Request(health_url,headers={'Authorization':'Bearer '+token} if token else {})
        with urlopen(request,timeout=10) as response: target=json.load(response)
    else:
        target={'provider':os.getenv('AGENTEVAL_TARGET_PROVIDER','company-api'),'model':os.getenv('AGENTEVAL_TARGET_MODEL')}
    if not isinstance(target,dict) or not isinstance(target.get('provider'),str): raise ValueError('Invalid target health metadata')
    return target
