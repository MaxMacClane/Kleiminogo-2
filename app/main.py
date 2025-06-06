import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api import survey
from app.api.stats import get_survey_statistics, generate_bokeh_charts, detect_device_type
from app.api.stats import get_survey_statistics_cached, generate_bokeh_charts_cached, get_comments_data_cached, get_all_comments_cached

app = FastAPI(
    title="Опрос жителей Клеймёново-2",
    description="API для сбора и анализа мнений жителей",
    version="1.0.0"
)

# Подключаем роуты опроса
app.include_router(survey.router)

# Подключаем папку со статикой (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем шаблоны Jinja2
templates = Jinja2Templates(directory="templates")

# Пример главной страницы (можно расширить)
from fastapi import Request
from fastapi.responses import HTMLResponse
import time

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/thanks", response_class=HTMLResponse)
def thanks(request: Request):
    return templates.TemplateResponse("thanks.html", {"request": request})

# Статистика с реальными данными и графиками Bokeh
@app.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    """Страница статистики с графиками"""
    user_agent = request.headers.get("user-agent", "")
    device_type = detect_device_type(user_agent)
    statistics = get_survey_statistics_cached()
    comments_data = get_comments_data_cached()
    bokeh_script, charts = generate_bokeh_charts_cached(statistics, device_type)
    t0 = time.time()
    resp = templates.TemplateResponse("stats.html", {
        "request": request,
        "statistics": statistics,
        "bokeh_script": bokeh_script,
        "charts": charts,
        "comments_data": comments_data
    })
    t1 = time.time()
    print(f"[PROFILE] Jinja2 stats.html render: {t1-t0:.3f}s")
    return resp

@app.get("/comments", response_class=HTMLResponse)
async def comments_page(request: Request):
    """Страница всех комментариев жителей"""
    all_comments = get_all_comments_cached()
    t0 = time.time()
    resp = templates.TemplateResponse("comments.html", {
        "request": request,
        "comments": all_comments,
        "total_count": len(all_comments)
    })
    t1 = time.time()
    print(f"[PROFILE] Jinja2 comments.html render: {t1-t0:.3f}s")
    return resp

@app.get("/consent", response_class=HTMLResponse)
def consent(request: Request):
    return templates.TemplateResponse("consent.html", {"request": request})

@app.get("/details", response_class=HTMLResponse)
def details(request: Request):
    return templates.TemplateResponse("survey-details.html", {"request": request})

# Для локального запуска и деплоя
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)