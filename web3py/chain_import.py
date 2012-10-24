__all__ = ['chain_import']

def chain_import(*statements):
    env = {}
    for s in statements:
        try:
            exec(s,{},env)
            return env[s.rsplit(' ')[-1]]
        except ImportError:
            pass
    raise ImportError
    
