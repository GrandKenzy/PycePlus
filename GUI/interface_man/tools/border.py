import pygame

def create_rounded_surface(base_surface: pygame.Surface, 
                           r1: bool = True, r2: bool = True, 
                           r3: bool = True, r4: bool = True, 
                           rwidth: int = 20, 
                           color: tuple[int, int, int, int] = (255, 0, 0, 128)
                          ) -> pygame.Surface:
    width, height = base_surface.get_size()
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    if any([r1, r2, r3, r4]):
        temp_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        tl = rwidth if r1 else 0
        tr = rwidth if r2 else 0
        br = rwidth if r3 else 0
        bl = rwidth if r4 else 0
        _draw_rounded_rect(temp_surf, color, pygame.Rect(0, 0, width, height), tl, tr, br, bl)
        surf.blit(temp_surf, (0, 0))
    surf.blit(base_surface, ((width - base_surface.get_width()) // 2,
                             (height - base_surface.get_height()) // 2))
    return surf

def _draw_rounded_rect(surface: pygame.Surface, color: tuple[int, int, int, int], 
                       rect: pygame.Rect, tl: int, tr: int, br: int, bl: int) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=0,
                     border_top_left_radius=tl,
                     border_top_right_radius=tr,
                     border_bottom_right_radius=br,
                     border_bottom_left_radius=bl)