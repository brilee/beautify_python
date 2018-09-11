import contextlib
import io
import textwrap
import unittest

from beautify import (beautify,
    DeMorganFlipper, DoubleNegativeCreator, NodeDepthAnnotator,
    IfDepthMaximizer, SafetyPasser, ForLoopUnroller
)

class TestBeautifier(unittest.TestCase):
    def assertEqualStdout(self, source1, source2):
        output_io1 = io.StringIO()
        output_io2 = io.StringIO()

        with contextlib.redirect_stdout(output_io1):
            exec(source1)

        with contextlib.redirect_stdout(output_io2):
            exec(source2)

        output_io1.seek(0)
        output_io2.seek(0)
        output1 = output_io1.read()
        output2 = output_io2.read()
        self.assertEqual(output1, output2)

    def test_fizzbuzz(self):

        source = textwrap.dedent('''
            for i in range(1, 101):
                if i % 3 == 0 and i % 5 == 0:
                    print ("fizzbuzz")
                elif i % 3 == 0:
                    print("fizz")
                elif i % 5 == 0:
                    print("buzz")
                else:
                    print(i)
        ''')        

        transformed_source = beautify((DeMorganFlipper,
               DoubleNegativeCreator,
               NodeDepthAnnotator,
               IfDepthMaximizer,
               ForLoopUnroller), source)
        self.assertEqualStdout(source, transformed_source)

if __name__ == '__main__':
    unittest.main()