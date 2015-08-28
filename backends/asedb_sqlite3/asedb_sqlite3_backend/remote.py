__author__ = 'Patrick Szmucer'

import json
import subprocess
from base64 import b64encode, b64decode
import abcd.results as results
from abcd.backend import CommunicationError

# Possible response codes from remote. See server.py for explanation
response_codes = ['200', '201', '202', '203', '204', '220', '221', '222', '223', '224']

def result_from_dct(result_type, **kwargs):
    '''
    Re-creates a result that was converted to a dictionary.
    '''
    if result_type == 'InsertResult':
        return results.InsertResult(kwargs['_inserted_ids'],
                                     kwargs['_skipped_ids'],
                                     kwargs['_msg'])
    elif result_type == 'UpdateResult':
        return results.UpdateResult(kwargs['_updated_ids'], 
                                    kwargs['_skipped_ids'], 
                                    kwargs['_upserted_ids'], 
                                    kwargs['_replaced_ids'], 
                                    kwargs['_msg'])
    elif result_type == 'RemoveResult':
        return results.RemoveResult(kwargs['_removed_count'], 
                                    kwargs['_msg'])
    elif result_type == 'AddKvpResult':
        return results.AddKvpResult(kwargs['_modified_ids'], 
                                    kwargs['_no_of_kvp_added'],
                                    kwargs['_msg'])
    elif result_type == 'RemoveKeysResult':
        return results.RemoveKeysResult(kwargs['_modified_ids'], 
                                        kwargs['_no_of_keys_removed'],
                                        kwargs['_msg'])
    else:
        raise NotImplementedError(result_type)

def communicate_with_remote(host, command):
    '''
    Sends a command to the remote host and interprets and returns the response.
    '''

    # Send command via the ssh to the remote host
    tty_flag = '-T'
    stdout=subprocess.PIPE
    stderr=subprocess.PIPE

    ssh_call = 'ssh -q {} {} '.format(tty_flag, host) + '\' {}\''.format(command)

    process = subprocess.Popen(ssh_call, shell=True, stdout=stdout, stderr=stderr)
    stdout, stderr = process.communicate()

    if len(stdout) < 5 or stdout[3] != ':':
        raise CommunicationError(stdout + '\n' + stderr)

    response_code = stdout[0:3]
    if response_code not in response_codes:
        raise CommunicationError('Unknown response code: {}'.format(response_code))

    data = stdout[4:]

    if response_code == '201':
        return b64decode(data)
    elif response_code == '202':
        return json.loads(b64decode(data))
    elif response_code == '203':
        return json.loads(b64decode(data))
    elif response_code == '204':
        return json.loads(b64decode(data))
    elif response_code == '220':
        return result_from_dct('InsertResult', **json.loads(b64decode(data)))
    elif response_code == '221':
        return result_from_dct('UpdateResult', **json.loads(b64decode(data)))
    elif response_code == '222':
        return result_from_dct('RemoveResult', **json.loads(b64decode(data)))
    elif response_code == '223':
        return result_from_dct('AddKvpResult', **json.loads(b64decode(data)))
    elif response_code == '224':
        return result_from_dct('RemoveKeysResult', **json.loads(b64decode(data)))
    else:
        raise CommunicationError('Unknown response code: {}'.format(response_code))