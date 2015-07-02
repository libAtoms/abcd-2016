

__author__ = 'Martin Uhrin'


class Result(object):
    def __init__(self, msg=None):
        self._msg = msg

    @property
    def msg(self):
        return self._msg


class RemoveResult(Result):
    def __init__(self, removed_count=1, msg=None):
        self._removed_count = removed_count
        super(RemoveResult, self).__init__(msg)

    @property
    def removed_count(self):
        """
        The number of entries removed
        :return: The number of entries removed
        """
        return self._removed_count


class InsertResult(Result):
    def __init__(self, inserted_ids, msg=None):
        self._inserted_ids = inserted_ids
        super(InsertResult, self).__init__(msg)

    @property
    def inserted_ids(self):
        return self._inserted_ids