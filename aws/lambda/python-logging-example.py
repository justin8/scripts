import sys
import logging
import traceback
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    '''Simple Lambda function.'''
    try:
        logger.info(f'event: {event}')
        artist = event['artist']
        logger.info(f'The artist is: {artist}')
        return {"status": "success", "message": None}
      
    except Exception as exp:
        exception_type, exception_value, exception_traceback = sys.exc_info()
        traceback_string = traceback.format_exception(exception_type, exception_value, exception_traceback)
        err_msg = json.dumps({
            "errorType": exception_type.__name__,
            "errorMessage": str(exception_value),
            "stackTrace": traceback_string
        })
        logger.error(err_msg)
