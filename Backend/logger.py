from logging import ERROR, INFO, CRITICAL, FileHandler, Filter, Formatter, StreamHandler, basicConfig, getLogger
from datetime import datetime
import pytz

from Backend.helper.observability import job_id, request_id

IST = pytz.timezone("Asia/Kolkata")


#----- Formatter that renders timestamps in IST
class ISTFormatter(Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        return dt.strftime(datefmt or "%d-%b-%y %I:%M:%S %p")


class CorrelationFilter(Filter):
    def filter(self, record):
        record.request_id = request_id()
        record.job_id = job_id()
        return True


#----- Root logging configuration
formatter = ISTFormatter(
    "[%(asctime)s] [%(levelname)s] [req=%(request_id)s job=%(job_id)s] - %(message)s",
    "%d-%b-%y %I:%M:%S %p",
)
file_handler = FileHandler("log.txt")
stream_handler = StreamHandler()
correlation_filter = CorrelationFilter()
file_handler.addFilter(correlation_filter)
stream_handler.addFilter(correlation_filter)
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

basicConfig(handlers=[file_handler, stream_handler], level=INFO)

getLogger("httpx").setLevel(ERROR)
getLogger("pyrogram").setLevel(ERROR)
getLogger("pyrogram.session").setLevel(CRITICAL)
getLogger("pyrogram.session.session").setLevel(CRITICAL)
getLogger("pyrogram.connection").setLevel(CRITICAL)
getLogger("fastapi").setLevel(ERROR)

LOGGER = getLogger(__name__)
LOGGER.setLevel(INFO)
LOGGER.info("Logger initialized with IST timezone.")
