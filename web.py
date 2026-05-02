from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView
from database.session import engine
from database.models import User, Pet, Marriage
from config import SUPERADMIN_ID

app = FastAPI(title="Orion Admin Panel")

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.tg_id, User.username, User.balance, User.level, User.warns_count]

class PetAdmin(ModelView, model=Pet):
    column_list = [Pet.id, Pet.owner_id, Pet.name, Pet.pet_type, Pet.level, Pet.satiety]

class MarriageAdmin(ModelView, model=Marriage):
    column_list = [Marriage.id, Marriage.user1_id, Marriage.user2_id, Marriage.wedding_date]

admin = Admin(app, engine)
admin.add_view(UserAdmin)
admin.add_view(PetAdmin)
admin.add_view(MarriageAdmin)

@app.get("/")
async def root():
    return {"message": "Orion Admin Panel"}

@app.middleware("http")
async def check_admin(request: Request, call_next):
    if request.url.path.startswith("/admin"):
        # Простая проверка, в реальности используй аутентификацию
        user_id = request.headers.get("X-User-ID")
        if user_id != str(SUPERADMIN_ID):
            return {"error": "Access denied"}
    response = await call_next(request)
    return response
