"""
Pyglet rendering utilities for OpenGL-accelerated drawing
Provides helper functions to mimic pygame drawing API but with OpenGL batching
"""
import pyglet
from pyglet import gl, shapes, text
import math
from typing import Tuple, List


class PygletRenderer:
    """High-performance OpenGL renderer for game elements"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.batch = pyglet.graphics.Batch()
        self.shapes_cache = []
        self.text_cache = []
        
    def clear_cache(self):
        """Clear cached shapes and text for next frame"""
        self.shapes_cache.clear()
        self.text_cache.clear()
        self.batch = pyglet.graphics.Batch()
    
    def flip_y(self, y: int) -> int:
        """Convert pygame Y coordinate to OpenGL (flip vertical)"""
        return self.height - y
    
    def draw_rect(self, color: Tuple[int, int, int], rect: Tuple[int, int, int, int], 
                  width: int = 0, alpha: int = 255):
        """Draw rectangle (filled if width=0, outlined otherwise)"""
        x, y, w, h = rect
        y_flipped = self.flip_y(y) - h
        
        if width == 0:
            # Filled rectangle
            rect_shape = shapes.Rectangle(
                x, y_flipped, w, h,
                color=(*color, alpha),
                batch=self.batch
            )
            self.shapes_cache.append(rect_shape)
        else:
            # Outlined rectangle - draw 4 lines
            # Top
            line1 = shapes.Line(x, y_flipped + h, x + w, y_flipped + h, 
                               color=(*color, alpha), batch=self.batch)
            line1.width = width
            # Right
            line2 = shapes.Line(x + w, y_flipped + h, x + w, y_flipped,
                               color=(*color, alpha), batch=self.batch)
            line2.width = width
            # Bottom
            line3 = shapes.Line(x + w, y_flipped, x, y_flipped,
                               color=(*color, alpha), batch=self.batch)
            line3.width = width
            # Left
            line4 = shapes.Line(x, y_flipped, x, y_flipped + h,
                               color=(*color, alpha), batch=self.batch)
            line4.width = width
            self.shapes_cache.extend([line1, line2, line3, line4])
    
    def draw_circle(self, color: Tuple[int, int, int], center: Tuple[int, int], 
                    radius: int, width: int = 0, alpha: int = 255):
        """Draw circle (filled if width=0, outlined otherwise)"""
        x, y = center
        y_flipped = self.flip_y(y)
        
        if width == 0:
            # Filled circle
            circle_shape = shapes.Circle(
                x, y_flipped, radius,
                color=(*color, alpha),
                batch=self.batch
            )
            self.shapes_cache.append(circle_shape)
        else:
            # Outlined circle (use arc)
            arc_shape = shapes.Arc(
                x, y_flipped, radius,
                color=(*color, alpha),
                batch=self.batch
            )
            self.shapes_cache.append(arc_shape)
    
    def draw_line(self, color: Tuple[int, int, int], start: Tuple[int, int], 
                  end: Tuple[int, int], width: int = 1, alpha: int = 255):
        """Draw line"""
        x1, y1 = start
        x2, y2 = end
        y1_flipped = self.flip_y(y1)
        y2_flipped = self.flip_y(y2)
        
        line = shapes.Line(
            x1, y1_flipped, x2, y2_flipped,
            color=(*color, alpha),
            batch=self.batch
        )
        line.width = width
        self.shapes_cache.append(line)
    
    def draw_text(self, text_str: str, x: int, y: int, font_name: str = 'Arial',
                  font_size: int = 16, color: Tuple[int, int, int] = (255, 255, 255),
                  bold: bool = False, anchor_x: str = 'left', anchor_y: str = 'top',
                  alpha: int = 255):
        """Draw text"""
        y_flipped = self.flip_y(y)
        
        label = text.Label(
            text_str,
            font_name=font_name,
            font_size=font_size,
            x=x, y=y_flipped,
            color=(*color, alpha),
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            batch=self.batch
        )
        self.text_cache.append(label)
    
    def draw_circular_progress(self, center: Tuple[int, int], radius: int,
                              progress: float, color: Tuple[int, int, int],
                              thickness: int = 4, alpha: int = 255):
        """Draw circular progress indicator"""
        x, y = center
        y_flipped = self.flip_y(y)
        
        # Draw background circle
        bg_circle = shapes.Arc(
            x, y_flipped, radius,
            color=(50, 50, 50, alpha),
            batch=self.batch
        )
        self.shapes_cache.append(bg_circle)
        
        # Draw progress arc
        if progress > 0:
            angle = progress * 360
            # Start from top (90 degrees in OpenGL)
            start_angle = 90
            arc = shapes.Arc(
                x, y_flipped, radius,
                angle=-angle,
                start_angle=start_angle,
                color=(*color, alpha),
                batch=self.batch
            )
            self.shapes_cache.append(arc)
    
    def draw_polygon(self, color: Tuple[int, int, int], points: List[Tuple[int, int]],
                     alpha: int = 255):
        """Draw filled polygon"""
        # Convert points to OpenGL coordinates
        gl_points = []
        for x, y in points:
            gl_points.extend([x, self.flip_y(y)])
        
        # Use OpenGL directly for polygons
        gl.glColor4ub(color[0], color[1], color[2], alpha)
        gl.glBegin(gl.GL_POLYGON)
        for i in range(0, len(gl_points), 2):
            gl.glVertex2f(gl_points[i], gl_points[i + 1])
        gl.glEnd()
    
    def draw_all(self):
        """Draw all batched shapes and text"""
        self.batch.draw()


class TextCache:
    """Cache for pre-rendered text labels"""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str, font_name: str, font_size: int, 
            color: Tuple[int, int, int], bold: bool = False) -> text.Label:
        """Get or create cached label"""
        cache_key = (key, font_name, font_size, color, bold)
        
        if cache_key not in self.cache:
            self.cache[cache_key] = text.Label(
                key,
                font_name=font_name,
                font_size=font_size,
                color=(*color, 255)
            )
        
        return self.cache[cache_key]
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()


class ShapeCache:
    """Cache for pre-rendered shapes"""
    
    def __init__(self):
        self.cache = {}
    
    def get_rect(self, key: str, x: int, y: int, width: int, height: int,
                 color: Tuple[int, int, int]) -> shapes.Rectangle:
        """Get or create cached rectangle"""
        cache_key = (key, width, height, color)
        
        if cache_key not in self.cache:
            self.cache[cache_key] = shapes.Rectangle(
                x, y, width, height,
                color=(*color, 255)
            )
        else:
            rect = self.cache[cache_key]
            rect.x = x
            rect.y = y
        
        return self.cache[cache_key]
    
    def get_circle(self, key: str, x: int, y: int, radius: int,
                   color: Tuple[int, int, int]) -> shapes.Circle:
        """Get or create cached circle"""
        cache_key = (key, radius, color)
        
        if cache_key not in self.cache:
            self.cache[cache_key] = shapes.Circle(
                x, y, radius,
                color=(*color, 255)
            )
        else:
            circle = self.cache[cache_key]
            circle.x = x
            circle.y = y
        
        return self.cache[cache_key]
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()
