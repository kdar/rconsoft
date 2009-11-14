# Read LICENSE for licensing details.
import re

#==============================
_camel_to_python_style_re = re.compile(r'([a-z])([A-Z])')
def camel_to_python_style(string):
  return _camel_to_python_style_re.sub('\\1_\\2', string).lower()
