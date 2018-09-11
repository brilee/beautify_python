import gast
import termcolor
import inspect


class PrettyPrinter(gast.NodeVisitor):
  """Print AST nodes."""

  def __init__(self, color):
    self.indent_lvl = 0
    self.result = ''
    self.color = color

  def _color(self, string, color, attrs=None):
    if self.color:
      return termcolor.colored(string, color, attrs=attrs)
    return string

  def _type(self, node):
    return self._color(node.__class__.__name__, None, ['bold'])

  def _field(self, name):
    return self._color(name, 'blue')

  def _value(self, name):
    return self._color(name, 'magenta')

  def _warning(self, name):
    return self._color(name, 'red')

  def _indent(self):
    return self._color('| ' * self.indent_lvl, None, ['dark'])

  def _print(self, s):
    self.result += s
    self.result += '\n'

  def generic_visit(self, node, name=None):
    if node._fields:
      cont = ':'
    else:
      cont = '()'

    if name:
      self._print('%s%s=%s%s' % (self._indent(), self._field(name),
                                 self._type(node), cont))
    else:
      self._print('%s%s%s' % (self._indent(), self._type(node), cont))

    self.indent_lvl += 1
    for f in node._fields + ('_statement_depth',):
      if not hasattr(node, f):
        self._print('%s%s' % (self._indent(), self._warning('%s=<unset>' % f)))
        continue
      v = getattr(node, f)
      if isinstance(v, list):
        if v:
          self._print('%s%s=[' % (self._indent(), self._field(f)))
          self.indent_lvl += 1
          for n in v:
            self.generic_visit(n)
          self.indent_lvl -= 1
          self._print('%s]' % (self._indent()))
        else:
          self._print('%s%s=[]' % (self._indent(), self._field(f)))
      elif isinstance(v, tuple):
        if v:
          self._print('%s%s=(' % (self._indent(), self._field(f)))
          self.indent_lvl += 1
          for n in v:
            self.generic_visit(n)
          self.indent_lvl -= 1
          self._print('%s)' % (self._indent()))
        else:
          self._print('%s%s=()' % (self._indent(), self._field(f)))
      elif isinstance(v, gast.AST):
        self.generic_visit(v, f)
      elif isinstance(v, str):
        self._print('%s%s=%s' % (self._indent(), self._field(f),
                                 self._value('"%s"' % v)))
      else:
        self._print('%s%s=%s' % (self._indent(), self._field(f),
                                 self._value(v)))
    self.indent_lvl -= 1

def fmt(node, color=True):
  printer = PrettyPrinter(True)
  if isinstance(node, (list, tuple)):
    for n in node:
      printer.visit(n)
  else:
    printer.visit(node)
  return printer.result

def fmt_src(src):
    print(fmt(gast.parse(src)))
