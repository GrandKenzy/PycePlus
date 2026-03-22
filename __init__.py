import pygame


pygame.init()

from PycePlus.UI import *
from PycePlus.GUI import *
from PycePlus.CORE.main import mainloop, Application
from PycePlus.CORE.events import register_button, register_custom_event, register_key
from PycePlus import __events__ as events
from PycePlus.CORE.timec import Time
from PycePlus.CORE.tools import asynchronous
from PycePlus.CORE.tools import network
from PycePlus.GUI import *