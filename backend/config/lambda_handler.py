from mangum import Mangum

from config.asgi import application

handler = Mangum(application, lifespan="off")
