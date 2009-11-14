#------------------------------
class SingletonType(type):
  """Implments a class as singleton. Just set __metaclass__ = SingletonType
  in your class."""
  #==============================
  def __call__(cls):
    if getattr(cls, '__instance__', None) is None:
      instance = cls.__new__(cls)
      instance.__init__()
      cls.__instance__ = instance
    return cls.__instance__