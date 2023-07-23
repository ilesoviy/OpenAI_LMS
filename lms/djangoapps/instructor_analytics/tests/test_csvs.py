""" Tests for analytics.csvs """


import pytest
from django.test import TestCase

from lms.djangoapps.instructor_analytics.csvs import create_csv_response, format_dictlist, format_instances


class TestAnalyticsCSVS(TestCase):
    """ Test analytics rendering of csv files."""

    def test_create_csv_response_nodata(self):
        header = ['Name', 'Email']
        datarows = []

        res = create_csv_response('robot.csv', header, datarows)
        assert res['Content-Type'] == 'text/csv'
        assert res['Content-Disposition'] == 'attachment; filename={}'.format('robot.csv')
        assert res.content.strip().decode('utf-8') == '"Name","Email"'

    def test_create_csv_response(self):
        header = ['Name', 'Email']
        datarows = [['Jim', 'jim@edy.org'], ['Jake', 'jake@edy.org'], ['Jeeves', 'jeeves@edy.org']]

        res = create_csv_response('robot.csv', header, datarows)
        assert res['Content-Type'] == 'text/csv'
        assert res['Content-Disposition'] == 'attachment; filename={}'.format('robot.csv')
        assert res.content.strip().decode('utf-8') ==\
               '"Name","Email"\r\n"Jim","jim@edy.org"\r\n"Jake","jake@edy.org"\r\n"Jeeves","jeeves@edy.org"'

    def test_create_csv_response_empty(self):
        header = []
        datarows = []

        res = create_csv_response('robot.csv', header, datarows)
        assert res['Content-Type'] == 'text/csv'
        assert res['Content-Disposition'] == 'attachment; filename={}'.format('robot.csv')
        assert res.content.strip().decode('utf-8') == ''


class TestAnalyticsFormatDictlist(TestCase):
    """ Test format_dictlist method """

    def test_format_dictlist(self):
        dictlist = [
            {
                'label1': 'value-1,1',
                'label2': 'value-1,2',
                'label3': 'value-1,3',
                'label4': 'value-1,4',
            },
            {
                'label1': 'value-2,1',
                'label2': 'value-2,2',
                'label3': 'value-2,3',
                'label4': 'value-2,4',
            }
        ]

        features = ['label1', 'label4']
        header, datarows = format_dictlist(dictlist, features)

        ideal_header = ['label1', 'label4']
        ideal_datarows = [['value-1,1', 'value-1,4'],
                          ['value-2,1', 'value-2,4']]

        assert header == ideal_header
        assert datarows == ideal_datarows

    def test_format_dictlist_empty(self):
        header, datarows = format_dictlist([], [])
        assert not header
        assert not datarows

    def test_create_csv_response(self):
        header = ['Name', 'Email']
        datarows = [['Jim', 'jim@edy.org'], ['Jake', 'jake@edy.org'], ['Jeeves', 'jeeves@edy.org']]

        res = create_csv_response('robot.csv', header, datarows)
        assert res['Content-Type'] == 'text/csv'
        assert res['Content-Disposition'] == 'attachment; filename={}'.format('robot.csv')
        assert res.content.strip().decode('utf-8') ==\
               '"Name","Email"\r\n"Jim","jim@edy.org"\r\n"Jake","jake@edy.org"\r\n"Jeeves","jeeves@edy.org"'


class TestAnalyticsFormatInstances(TestCase):
    """ test format_instances method """

    class TestDataClass:
        """ Test class to generate objects for format_instances """
        def __init__(self):
            self.a_var = 'aval'
            self.b_var = 'bval'
            self.c_var = 'cval'

        @property
        def d_var(self):
            """ accessor to see if they work too """
            return 'dval'

    def setUp(self):
        super().setUp()
        self.instances = [self.TestDataClass() for _ in range(5)]

    def test_format_instances_response(self):
        features = ['a_var', 'c_var', 'd_var']
        header, datarows = format_instances(self.instances, features)
        assert header == ['a_var', 'c_var', 'd_var']
        assert datarows == [['aval', 'cval', 'dval'] for _ in range(len(self.instances))]

    def test_format_instances_response_noinstances(self):
        features = ['a_var']
        header, datarows = format_instances([], features)
        assert header == features
        assert datarows == []

    def test_format_instances_response_nofeatures(self):
        header, datarows = format_instances(self.instances, [])
        assert header == []
        assert datarows == [[] for _ in range(len(self.instances))]

    def test_format_instances_response_nonexistantfeature(self):
        with pytest.raises(AttributeError):
            format_instances(self.instances, ['robot_not_a_real_feature'])
