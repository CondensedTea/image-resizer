import base64
import tempfile
from io import BytesIO
from typing import Any, Dict, Union

from fastapi import Depends, FastAPI, File, Query, status
from fastapi.responses import FileResponse, JSONResponse, Response
from PIL import Image
from redis import Redis

from app.exceptions import ImageNotFound, WrongAspectRatio
from app.pydantic_models import AddTask, GetTask


def redis_connection() -> Redis:  # type: ignore
    r = Redis(host='redis', port=6379, db=0, encoding='utf-8')
    return r


app = FastAPI()


@app.exception_handler(WrongAspectRatio)
def wrong_aspect_ratio(
    response: Response, exc: WrongAspectRatio  # pylint:disable=unused-argument
) -> Response:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={'error': 'image must be square'},
    )


@app.exception_handler(ImageNotFound)
def image_not_found(
    response: Response, exc: WrongAspectRatio  # pylint:disable=unused-argument
) -> Response:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={'error': 'image not found'},
    )


@app.post('/tasks', status_code=status.HTTP_201_CREATED, response_model=AddTask)
def add_task(
    file: bytes = File(...), redis: Redis = Depends(redis_connection)  # type: ignore
) -> AddTask:
    r = redis
    task_id = str(r.incr('id'))
    im_file = BytesIO(file)
    img = Image.open(im_file)
    if not img.width == img.height:
        raise WrongAspectRatio
    f64 = base64.b64encode(file)
    r.set(task_id + '_original', f64)
    r.lpush('default', task_id)
    r.set(task_id + '_status', 'WAITING')
    return AddTask(id=int(task_id))


@app.get('/tasks/{task_id}', status_code=status.HTTP_200_OK)
def get_task(
    task_id: str,
    size: str = Query(None, regex='(64|32|original)'),
    redis: Redis = Depends(redis_connection),  # type: ignore
) -> Union[GetTask, FileResponse, Dict[Any, Any]]:
    r = redis
    if size is None:
        return GetTask(status=r.get(task_id + '_status'))
    img = r.get('{}_{}'.format(task_id, size))
    if img is None:
        raise ImageNotFound
    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.png', delete=False) as FOUT:
        FOUT.write(base64.b64decode(img))
    return FileResponse(FOUT.name, media_type='image/png')
