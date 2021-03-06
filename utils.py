# pyncoin/utils.py

import binascii
import decimal
import traceback

try:
    import simplejson as json
except ImportError:
    import json

''' Utility functions '''

def bytes_to_int(data):
    ''' Converts a binary data to an integer.
        Params:
            - data (bytes): The binary data
        Returns (int): The integer
    '''
    return int(binascii.hexlify(data), 16)

def bytes_to_hex(data):
    ''' Converts a binary data to a hexadecimal string.
        Params:
            - data (bytes): The binary data
        Returns (str): The hexadecimal string
    '''
    return binascii.hexlify(data)

def int_to_bytes(number):
    ''' Converts an integer into binary data.
        Params:
            - number (int): The integer
        Returns (bytes): The binary data
    '''
    hx = format(number, 'x')
    if len(hx) % 2:
        hx = '0' + hx
    return binascii.unhexlify(hx)

def hex_to_bytes(hexstr):
    ''' Converts a hexadecimal string into binary data.
        Params:
            - hexstr (str): The hexadecimal string
        Returns (bytes): The binary data
    '''
    try:
        result = binascii.unhexlify(hexstr)
    except binascii.Error as e:
        raise BadRequestError('invalid hex parameter', 
            {'offending_value': hexstr, 'cause': str(e)})
    return result

class RawSerializable:
    ''' Base class for raw serializable objects. 

    This class can be used as-is or it can be subclassed. If used directly, it provides an
    extended functionality of python objects' `__dict__` method serializing the attributes
    of the object recursively if the attributes are themselves instances of RawSerializable.

    Subclassing this class and overriding `from_raw` and `to_raw` method allows you to 
    customize the serialization method. For example it should be easy to add json 
    serialization support to any custom objects.
    '''

    @classmethod
    def from_raw(cls, raw_obj):
        ''' Returns a new instance initialized from a raw dictionary. 

        Override this method to initialize the attributes of this class from a dictionary.

        Params:
            - raw_obj (dict): The raw object.

        Returns (cls): An instance of this class, initialized from `raw_obj`.
        '''
        obj = cls()
        obj.__dict__.update({ key: cls.value_from_raw(value) 
                                for (key, value) in raw_obj.items() })
        return obj

    def to_raw(self):
        ''' Converts this instance to a raw dictionary.

        Override this method to convert the attributes of this class in the resulting 
        dictionary.

        Retuns (dict): This instance represented as a dictionary.
        '''
        return { key: self.__class__.value_to_raw(value) 
                    for key, value in self.__dict__.items() }

    @classmethod
    def value_from_raw(cls, raw_value):
        ''' Converts a raw value to the instances of this class or a list of instances
        objects if possible.

        You probably don't want to override this method.

        Params: 
            - raw_value (any): The raw object. If it is a dict it will be converted to the 
                instance of this class. If it is a list, its elements will be converted 
                to instances of this class. Otherwise the parameter will be returned.

        Returns (any): The raw object converted to the instancess of this class.
        '''
        if isinstance(raw_value, dict):
            return cls.from_raw(raw_value)
        elif isinstance(raw_value, list):
            return [cls.value_from_raw(item) for item in raw_value]
        else:
            return raw_value

    @classmethod
    def value_to_raw(cls, value):
        ''' Converts the instances of this class to raw values if possible.

        You probably don't want to override this method.

        Params: 
            - value (any): The object to be converted. If it is an instance of `RawSerializable`,
                it will be converted to raw value. If it is a list, its elements will 
                be converted to raw values. Otherwise the parameter will be returned.

        Returns (any): The raw object.
        '''
        if isinstance(value, RawSerializable):
            return value.to_raw()
        elif isinstance(value, list):
            return [cls.value_to_raw(item) for item in value]
        else:
            return value

    @classmethod
    def from_raw_list(cls, raw_list):
        ''' Converts a list of raw objects to instances of this class.

        You probably don't want to override this method.

        Params:
            - raw_list (list): The list of raw objects.

        Returns (list): The list of converted objects.
        '''
        return [cls.value_from_raw(raw_obj) for raw_obj in raw_list]

    @classmethod
    def to_raw_list(cls, objs):
        return [obj.to_raw() for obj in objs]

    @classmethod
    def to_json_any(cls, value):
        ''' Converts an instance or a list of instances of this class to a json string.

        Params:
            - value (any): The instance of this class or a list of instances of this class.
        
        Returns (str): The input represented as a json string.
        '''
        return json.dumps(cls.value_to_raw(value))

    def to_json(self):
        ''' Converts this object to a json string.

        You probably don't want to override this method.

        Returns (str): This object represented as a json string.
        '''
        return json.dumps(self.to_raw())

    @classmethod
    def from_json(cls, json_str):
        ''' Initializes an instance or a list of instances of this class from a json string.

        You probably don't want to override this method.

        Params:
            - json_str (str): json object in string format

        Returns (list or cls): An instance or a list of instances of this class.
        '''
        raw = json.loads(json_str, parse_float=decimal.Decimal)
        return cls.value_from_raw(raw)

    def to_bin(self):
        ''' Converts this object to a binary format. '''
        return self.to_json().encode('utf-8')

    @classmethod
    def from_bin(cls, json_bin):
        ''' Returns a new instance initialized from the binary format. '''
        return cls.from_json(json_bin.decode('utf-8'))

    def __repr__(self):
        return self.to_json()

    def __eq__(self, other):
        return isinstance(self, other.__class__) and self.to_raw() == other.to_raw()

    def __hash__(self):
        return hash(frozenset(self.to_raw()))

class HttpError(Exception, RawSerializable):
    def __init__(self, message, status_code, payload=None):
        Exception.__init__(self)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_raw(self):
        raw = { 'error': self.__class__.__name__, 'message': self.message }
        if self.payload is not None:
            raw['payload'] = self.payload
        return raw

    @classmethod
    def from_raw(cls, raw_obj):
        raise AssertionError('HttpError must not be initialized from raw objects.')

class BadRequestError(HttpError):
    status_code = 400
    def __init__(self, message, payload=None):
        HttpError.__init__(self, message, BadRequestError.status_code, payload)

class UnauthorizedError(HttpError):
    status_code = 401
    def __init__(self, message, payload=None):
        HttpError.__init__(self, message, UnauthorizedError.status_code, payload)

class ForbiddenError(HttpError):
    status_code = 403
    def __init__(self, message, payload=None):
        HttpError.__init__(self, message, ForbiddenError.status_code, payload)

class NotFoundError(HttpError):
    status_code = 404
    def __init__(self, message, payload=None):
        HttpError.__init__(self, message, NotFoundError.status_code, payload)

def format_exception(ex):
    fmt = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
    return ''.join(fmt)

def get_param(params, param_name):
    MISSING_PARAM_PLACEHOLDER = '$$$missing_param$$$'
    data = params.get(param_name, MISSING_PARAM_PLACEHOLDER)
    if data == MISSING_PARAM_PLACEHOLDER:
        raise BadRequestError('missing parameter', {'parameter': param_name})
    return data
