from ctq import acquire


class RecordExtras:

    def edit(self, **kwargs):
        """Proxy the edit function on the parent collection object.
        """
        return acquire(self.__parent__).edit(self, *args, **kwargs)

    def rename(self, name):
        """Proxy the rename function on the parent collection object.
        """
        return acquire(self.__parent__).rename(self,name)
    
    def delete(self):
        """Proxy the delete function on the parent collection object.
        """
        return acquire(self.__parent__).delete(self)