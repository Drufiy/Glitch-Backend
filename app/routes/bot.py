from fastapi import APIRouter, HTTPException
from app.models.model import DiagnoseRequest, DiagnoseResponse
from app.utils.utils import generate_diagnosis

router = APIRouter()

@router.post("/diagnose", response_model=DiagnoseResponse)
def diagnose(request: DiagnoseRequest):
    """Diagnose a technical problem with session history"""
    
    try:
        result = generate_diagnosis(
            problem=request.problem, 
            command_output=request.command_output,
            session_id=request.session_id
        )
        
        return DiagnoseResponse(
            message=result["message"],
            command=result["command"],
            next_step=result["next_step"],
            session_id=result["session_id"],
            history=result["history"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))