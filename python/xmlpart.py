# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Itaapy, ArsAperta, Pierlis, Talend

# Import from the Standard Library
from copy import deepcopy
from cStringIO import StringIO
from re import search, compile

# Import from lxml
from lxml.etree import parse, fromstring, tostring, _Element
from lxml.etree import _ElementStringResult, _ElementUnicodeResult

# Import from lpod
from utils import _get_abspath, DateTime, convert_unicode
from utils import _make_xpath_query


ODF_NAMESPACES = {
    'office': "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    'style': "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    'text': "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    'presentation': "urn:oasis:names:tc:opendocument:xmlns:presentation:1.0",
    'table': "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    'draw': "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    'fo': "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    'xlink': "http://www.w3.org/1999/xlink",
    'dc': "http://purl.org/dc/elements/1.1/",
    'meta': "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    'number': "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    'svg': "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    'chart': "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    'dr3d': "urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",
    'math': "http://www.w3.org/1998/Math/MathML",
    'form': "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
    'script': "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
    'ooo': "http://openoffice.org/2004/office",
    'ooow': "http://openoffice.org/2004/writer",
    'oooc': "http://openoffice.org/2004/calc",
    'dom': "http://www.w3.org/2001/xml-events",
    'xforms': "http://www.w3.org/2002/xforms",
    'xsd': "http://www.w3.org/2001/XMLSchema",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
    'rpt': "http://openoffice.org/2005/report",
    'of': "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
    'rdfa': "http://docs.oasis-open.org/opendocument/meta/rdfa#",
    'config': "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}


FIRST_CHILD, LAST_CHILD, NEXT_SIBLING, PREV_SIBLING, STOPMARKER = range(5)


ns_stripper = compile(' xmlns:\w*="[\w:\-\/\.#]*"')


# An empty XML document with all namespaces declared
ns_document_path = _get_abspath('templates/namespaces.xml')
with open(ns_document_path, 'rb') as file:
    ns_document_data = file.read()



def decode_qname(qname):
    """Turn a prefixed name to a (uri, name) pair.
    """
    if ':' in qname:
        prefix, name = qname.split(':')
        try:
            uri = ODF_NAMESPACES[prefix]
        except IndexError:
            raise ValueError, "XML prefix '%s' is unknown" % prefix
        return uri, name
    return None, qname



def uri_to_prefix(uri):
    """Find the prefix associated to the given URI.
    """
    for key, value in ODF_NAMESPACES.iteritems():
        if value == uri:
            return key
    raise ValueError, 'uri "%s" not found' % uri



def get_prefixed_name(tag):
    """Replace lxml "{uri}name" syntax with "prefix:name" one.
    """
    uri, name = tag.split('}', 1)
    prefix = uri_to_prefix(uri[1:])
    return '%s:%s' % (prefix, name)



class_registry = {}

def register_element_class(qname, cls):
    # Turn tag name into what lxml is expecting
    tag = '{%s}%s' % decode_qname(qname)
    if tag in class_registry:
        raise ValueError,  'element "%s" already registered' % qname
    class_registry[tag] = cls



def make_odf_element(native_element):
    cls = class_registry.get(native_element.tag,  odf_element)
    return cls(native_element)



def odf_create_element(element_data):
    if not isinstance(element_data, (str, unicode)):
        raise TypeError, "element data is not str/unicode"
    if not element_data.strip():
        raise ValueError, "element data is empty"
    element_data = convert_unicode(element_data)
    data = ns_document_data.format(element=element_data)
    root = fromstring(data)
    return make_odf_element(root[0])



class odf_element(object):
    """Representation of an XML element.
    Abstraction of the XML library behind.
    """

    def __init__(self, native_element):
        if not isinstance(native_element, _Element):
            raise TypeError, ('"%s" is not an element node' %
                              type(native_element))
        self.__element = native_element


    def __str__(self):
        return '%s "%s"' % (object.__str__(self), self.get_name())


    # TODO wrap_text must a private function
    def wrap_text(self, element, offset=0, length=0):
        current = self.__element
        element = element.__element

        total = 0
        for text in current.xpath('text()'):
            total += len(text)
            if offset < total:
                left = text[:-(total - offset)]
                right = text[-(total - offset):]
                center, right = right[:length], right[length:]

                element.tail = right
                if center:
                    element.text = center

                if text.is_tail:
                    owner = text.getparent()

                    # Set text
                    owner.tail = left

                    # Insert element
                    index = current.index(owner)
                    current.insert(index + 1, element)
                    return
                else:
                    # Set text
                    current.text = left

                    # Insert element
                    current.insert(0, element)
                    return
        else:
            # offset is too big => insert at the end
            current.append(element)
            return


    def get_name(self):
        element = self.__element
        return get_prefixed_name(element.tag)


    def get_element_list(self, xpath_query):
        element = self.__element
        result = element.xpath(xpath_query, namespaces=ODF_NAMESPACES)
        return [make_odf_element(e) for e in result]


    def get_element(self, xpath_query):
        result = self.get_element_list(xpath_query)
        if result:
            return result[0]
        return None


    def get_attributes(self):
        attributes = {}
        element = self.__element
        for key, value in element.attrib.iteritems():
            attributes[get_prefixed_name(key)] = value
        # FIXME lxml has mixed bytestring and unicode
        return attributes


    def get_attribute(self, name):
        element = self.__element
        uri, name = decode_qname(name)
        if uri is None:
            return element.get(name)
        value = element.get('{%s}%s' % (uri, name))
        if value is None:
            return None
        return unicode(value)


    def set_attribute(self, name, value):
        element = self.__element
        uri, name = decode_qname(name)
        if uri is None:
            element.set(name, value)
        else:
            element.set('{%s}%s' % (uri, name), value)


    def del_attribute(self, name):
        element = self.__element
        uri, name = decode_qname(name)
        if uri is None:
            del element.attrib[name]
        else:
            del element.attrib['{%s}%s' % (uri, name)]


    def get_text(self):
        result = []
        for obj in self.xpath('text:p|text:span|text:a|text()'):
            if isinstance(obj, odf_element):
                result.append(obj.get_text())
            else:
                result.append(obj)
        return u''.join(result)


    def set_text(self, text, after=False):
        """If "after" is true, sets the text at the end of the element, not
        inside.
        FIXME maybe too specific to lxml, see at the end if disposable
        """
        element = self.__element
        if after:
            element.tail = text
        else:
            element.text = text


    def match(self, pattern):
        """ True if the text of the odf_element match one or more times the
            pattern.
        """
        text = self.get_text()
        return search(pattern, text) is not None


    def get_parent(self):
        element = self.__element
        parent = element.getparent()
        if parent is None:
            # Already at root
            return None
        return make_odf_element(parent)


    def get_next_sibling(self):
        element = self.__element
        next = element.getnext()
        if next is None:
            return None
        return make_odf_element(next)


    def get_prev_sibling(self):
        element = self.__element
        prev = element.getprevious()
        if prev is None:
            return None
        return make_odf_element(prev)


    def get_children(self):
        element = self.__element
        return [make_odf_element(e) for e in element]


    #
    # Shortcuts expected to be reusable over several elements
    #

    def get_creator(self):
        dc_creator = self.get_element('dc:creator')
        if dc_creator is None:
            return None
        return dc_creator.get_text()


    def set_creator(self, creator):
        dc_creator = self.get_element('dc:creator')
        if dc_creator is None:
            dc_creator = odf_create_element('<dc:creator/>')
            self.append_element(dc_creator)
        dc_creator.set_text(creator)


    def get_date(self):
        dc_date = self.get_element('dc:date')
        if dc_date is None:
            return None
        date = dc_date.get_text()
        return DateTime.decode(date)


    def set_date(self, date):
        dc_date = self.get_element('dc:date')
        if dc_date is None:
            dc_date = odf_create_element('<dc:date/>')
            self.append_element(dc_date)
        dc_date.set_text(DateTime.encode(date))


    def get_text_content(self):
        """Like "get_text" but applied to the embedded paragraph:
        annotations, cells...
        """
        element = self.__element
        text = element.xpath('string(text:p)', namespaces=ODF_NAMESPACES)
        return unicode(text)


    def set_text_content(self, text):
        """Like "set_text" but applied to the embedded paragraph:
        annotations, cells...
        """
        paragraph = self.get_element('text:p')
        if paragraph is None:
            paragraph = odf_create_element('<text:p/>')
            self.insert_element(paragraph, FIRST_CHILD)
        element = paragraph.__element
        element.clear()
        element.text = text


    def insert_element(self, element, xmlposition):
        current = self.__element
        element = element.__element
        if xmlposition is FIRST_CHILD:
            current.insert(0, element)
        elif xmlposition is LAST_CHILD:
            current.append(element)
        elif xmlposition is NEXT_SIBLING:
            parent = current.getparent()
            index = parent.index(current)
            parent.insert(index + 1, element)
        elif xmlposition is PREV_SIBLING:
            parent = current.getparent()
            index = parent.index(current)
            parent.insert(index, element)
        else:
            raise ValueError, "xmlposition must be defined"


    def append_element(self, element):
        """Shortcut to insert at the end.
        """
        self.insert_element(element, LAST_CHILD)


    def xpath(self, xpath_query):
        element = self.__element
        elements = element.xpath(xpath_query, namespaces=ODF_NAMESPACES)
        result = []
        for obj in elements:
            # The results of a xpath query can be a str
            if type(obj) is _ElementStringResult:
                result.append(str(obj))
            elif type(obj) is _ElementUnicodeResult:
                result.append(unicode(obj))
            else:
                result.append(make_odf_element(obj))
        return result


    def clear(self):
        element = self.__element
        element.clear()
        element.text = None


    def clone(self):
        element = self.__element
        return self.__class__(deepcopy(element))


    def serialize(self):
        element = deepcopy(self.__element)
        # XXX hack over lxml: remove text outside the element
        element.tail = None
        data = tostring(element)
        # XXX hack over lxml: remove namespaces
        return ns_stripper.sub('', data)


    def delete(self, child):
        element = self.__element
        element.remove(child.__element)



class odf_xmlpart(object):
    """Representation of an XML part.
    Abstraction of the XML library behind.
    """
    def __init__(self, part_name, container):
        self.part_name = part_name
        self.container = container

        # Internal state
        self.__tree = None
        self.__root = None


    def __get_tree(self):
        if self.__tree is None:
            container = self.container
            part = container.get_part(self.part_name)
            self.__tree = parse(StringIO(part))
        return self.__tree


    #
    # Non-public yet useful helpers
    #

    def _get_element_list(self, element_name, style=None, family=None,
                          draw_name=None, draw_style=None, table_name=None,
                          note_class=None, style_name=None, text_id=None,
                          text_name=None, office_name=None, office_title=None,
                          level=None, href=None, position=None, regex=None,
                          context=None):
        query = _make_xpath_query(element_name, style=style, family=family,
                                  draw_name=draw_name,
                                  draw_style=draw_style,
                                  table_name=table_name,
                                  style_name=style_name,
                                  note_class=note_class, text_id=text_id,
                                  text_name=text_name, office_name=office_name,
                                  office_title=office_title,
                                  level=level, position=position,
                                  context=context)
        if regex or href:
            raise NotImplementedError
        if context is None:
            return self.get_element_list(query)
        return context.get_element_list(query)


    def _get_element(self, element_name, style=None, family=None,
                     draw_name=None, table_name=None, style_name=None,
                     text_id=None, text_name=None, office_name=None,
                     office_title=None, level=None, href=None, position=None,
                     regex=None, context=None):
        result = self._get_element_list(element_name, style=style,
                                        family=family, draw_name=draw_name,
                                        table_name=table_name,
                                        style_name=style_name,
                                        text_id=text_id, text_name=text_name,
                                        office_name=office_name,
                                        office_title=office_title, level=level,
                                        href=href, position=position,
                                        regex=regex, context=context)
        if result:
            return result[0]
        return None


    #
    # Public API
    #

    def get_root(self):
        if self.__root is None:
            tree = self.__get_tree()
            self.__root = odf_element(tree.getroot())
        return self.__root


    def get_element_list(self, xpath_query):
        root = self.get_root()
        return root.xpath(xpath_query)


    def get_element(self, xpath_query):
        result = self.get_element_list(xpath_query)
        if not result:
            return None
        return result[0]


    def clone(self):
        clone = object.__new__(self.__class__)
        for name in self.__dict__:
            if name == 'container':
                setattr(clone, name, self.container.clone())
            elif name in ('_odf_xmlpart__tree',):
                setattr(clone, name, None)
            else:
                value = getattr(self, name)
                value = deepcopy(value)
                setattr(clone, name, value)
        return clone


    def serialize(self, pretty=False):
        tree = self.__get_tree()
        # lxml declaration is too exotic too me
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                + tostring(tree, encoding='UTF-8', pretty_print=pretty))


    def delete(self, child):
        parent = child.get_parent()
        parent.delete(child)
