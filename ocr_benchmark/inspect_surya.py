import inspect
from surya.recognition import RecognitionPredictor
print("Signature:", inspect.signature(RecognitionPredictor.__call__))
print("Doc:", inspect.getdoc(RecognitionPredictor.__call__))
