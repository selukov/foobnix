import unittest
from foobnix.util.text_utils import smart_splitter, capitilize_string, \
    capitilize_query, split_string

class TestCapitalizeFunctions(unittest.TestCase):
    def test_capitilize_None(self):
        self.assertEquals(None, capitilize_string(None))
        self.assertEquals("", capitilize_string(""))
        
    def test_capitilize(self):
        self.assertEquals(u"Madonna Music", capitilize_string("MaDoNna MUSIC"))
        self.assertEquals(u"Madonna", capitilize_string("MaDoNna"))

class TestCapitalizeQueryFunctions(unittest.TestCase):
    def test_capitilize_None(self):
        self.assertEquals(None, capitilize_query(None))
        self.assertEquals("", capitilize_query(""))
        
    def test_capitilize_url(self):
        self.assertEquals(u"http://Madonna", capitilize_query("http://Madonna"))
    
    def test_capitilize_sring(self):
        self.assertEquals(u"Ddt", capitilize_query("ddt"))
        self.assertEquals(u"DDT", capitilize_query("DDT"))
        self.assertEquals(u"DDT Music", capitilize_query("DDT music"))


class TestSplitterFunctions(unittest.TestCase):
    def setUp(self):
        self.input = "abcde 1234 w2e3"
    
    def test_empty_string(self):
        result = smart_splitter(None, 3)
        self.assertEquals(None, result)
        
    def test_empty_len(self):
        result = smart_splitter("100", None)
        self.assertEquals(["100"], result)
        
    def test_good_splitter(self):
        result = smart_splitter(self.input, 4)
        self.assertEquals(["abcde", "1234", "w2e3"], result)
    
    def test_good_splitter1(self):
        result = smart_splitter(self.input, 2)
        self.assertEquals(["abcde", "1234", "w2"], result)


class TestSplitStringFunction(unittest.TestCase):
    def setUp(self):
        self.input = "abcde,1234 w2    e3fdfd"
    
    def test_empty_string(self):
        result = split_string("", 3)
        self.assertEquals("", result)
        
    def test_empty_len(self):
        result = split_string("100", 3)
        self.assertEquals("100\n", result)
        
    def test_good_splitter(self):
        result = split_string(self.input, 10)
        self.assertEquals("abcde,\n1234 w2\ne3fdfd", result)
    
    def test_good_splitter1(self):
        result = split_string(self.input, 19)
        self.assertEquals("abcde,1234 w2\ne3fdfd", result)


if __name__ == '__main__':
    unittest.main()
