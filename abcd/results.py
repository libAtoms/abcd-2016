

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
    def __init__(self, inserted_ids, skipped_ids, replaced_ids, msg=None):
        self._inserted_ids = inserted_ids
        self._skipped_ids = skipped_ids
        self._replaced_ids = replaced_ids
        super(InsertResult, self).__init__(msg)

    @property
    def inserted_ids(self):
        return self._inserted_ids

    @property
    def skipped_ids(self):
        return self._skipped_ids

    @property
    def replaced_ids(self):
        return self._replaced_ids

class UpdateResult(Result):
    def __init__(self, updated_ids, skipped_ids, inserted_ids, msg=None):
        self._updated_ids = updated_ids
        self._skipped_ids = skipped_ids
        self._inserted_ids = inserted_ids
        super(UpdateResult, self).__init__(msg)

    @property
    def updated_ids(self):
        return self._updated_ids

    @property
    def skipped_ids(self):
        return self._skipped_ids

    @property
    def inserted_ids(self):
        return self._inserted_ids

class AddKvpResult(Result):
    def __init__(self, modified_ids, no_of_kvp_added, msg=None):
        self._modified_ids = modified_ids
        self._no_of_kvp_added = no_of_kvp_added
        super(AddKvpResult, self).__init__(msg)

    @property
    def modified_ids(self):
        return self._modified_ids

    @property
    def no_of_kvp_added(self):
        return self._no_of_kvp_added

class RemoveKeysResult(Result):
    def __init__(self, modified_ids, no_of_keys_removed, msg=None):
        self._modified_ids = modified_ids
        self._no_of_keys_removed = no_of_keys_removed
        super(RemoveKeysResult, self).__init__(msg)

    @property
    def modified_ids(self):
        return self._modified_ids

    @property
    def no_of_keys_removed(self):
        return self._no_of_keys_removed