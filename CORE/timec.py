import pygame



class Time:
    seconds = 0
    current_ticks = pygame.time.get_ticks() / 1000
    keys: dict[str, int] = {}

    @classmethod
    def format(cls):
        # devuelve seconds en hh:mm:ss
        return f"{cls.seconds // 3600:02d}:{(cls.seconds // 60) % 60:02d}:{cls.seconds % 60:02d}"


    @classmethod
    def wait(cls, key: str, seconds: int, reset: bool = False):
        current = cls.keys.get(key, None)
    
        if not current is None:
            if cls.current_ticks - current >= seconds:
                if reset:
                    cls.keys[key] = cls.current_ticks
                return True
        else:
            cls.keys[key] = cls.current_ticks
        return False