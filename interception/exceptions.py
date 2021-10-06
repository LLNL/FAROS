class FAROSException(Exception):
  pass

class CommandException(FAROSException):
  pass

class CompileException(FAROSException):
  pass

class EmptyFileException(FAROSException):
  pass
