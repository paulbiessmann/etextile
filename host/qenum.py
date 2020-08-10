def qenum_key(base, value, add_base=False, klass=None):
    """Convert a Qt Enum value to its key as a string.
    Args:
        base: The object the enum is in, e.g. QFrame.
        value: The value to get.
        add_base: Whether the base should be added to the printed name.
        klass: The enum class the value belongs to.
               If None, the class will be auto-guessed.
    Return:
        The key associated with the value as a string if it could be found.
        The original value as a string if not.
    """
    if klass is None:
        klass = value.__class__
        if klass == int:
            raise TypeError("Can't guess enum class of an int!")

    try:
        idx = base.staticMetaObject.indexOfEnumerator(klass.__name__)
        ret = base.staticMetaObject.enumerator(idx).valueToKey(value)
    except AttributeError:
        ret = None

    if ret is None:
        for name, obj in vars(base).items():
            if isinstance(obj, klass) and obj == value:
                ret = name
                break
        else:
            ret = '0x{:04x}'.format(int(value))

    if add_base and hasattr(base, '__name__'):
        return '.'.join([base.__name__, ret])
    else:
        return ret
