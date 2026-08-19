from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth ----------
class PlayerOption(ORMModel):
    id: int
    name: str


class PlayerLogin(BaseModel):
    user_id: int
    pin: str = Field(min_length=4, max_length=8)


class CoachLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ---------- Usuarios / grupos ----------
class GroupOut(ORMModel):
    id: int
    name: str


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class UserOut(ORMModel):
    id: int
    name: str
    role: str
    is_active: bool
    groups: list[GroupOut] = []


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    pin: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")
    group_ids: list[int] = []


class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    pin: str | None = Field(default=None, min_length=4, max_length=8, pattern=r"^\d+$")
    is_active: bool | None = None
    group_ids: list[int] | None = None


# ---------- Ejercicios ----------
class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    category: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class ExerciseOut(ORMModel):
    id: int
    name: str
    description: str | None
    category: str | None
    is_active: bool


# ---------- Rutinas ----------
class RoutineExerciseIn(BaseModel):
    # Al editar, el id identifica al ejercicio que ya estaba en la batería para
    # conservarlo (y con él las cargas ya registradas). Vacío = ejercicio nuevo.
    id: int | None = None
    exercise_id: int
    sets: int = Field(default=3, ge=1, le=20)
    target_reps: int | None = Field(default=None, ge=1, le=200)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    notes: str | None = None


class RoutineExerciseOut(ORMModel):
    id: int
    position: int
    sets: int
    target_reps: int | None
    rest_seconds: int | None
    notes: str | None
    exercise: ExerciseOut


class AssignmentIn(BaseModel):
    target_type: str = Field(pattern=r"^(all|group|player)$")
    group_id: int | None = None
    user_id: int | None = None


class AssignmentOut(ORMModel):
    id: int
    target_type: str
    group_id: int | None
    user_id: int | None


class RoutineIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    session_date: date
    notes: str | None = None
    items: list[RoutineExerciseIn] = []
    assignments: list[AssignmentIn] = []


class RoutineOut(ORMModel):
    id: int
    name: str
    session_date: date
    notes: str | None
    items: list[RoutineExerciseOut] = []
    assignments: list[AssignmentOut] = []


class RoutineSummary(ORMModel):
    id: int
    name: str
    session_date: date
    exercise_count: int = 0
    assigned_players: int = 0


# ---------- Cargas ----------
class SetLogIn(BaseModel):
    routine_exercise_id: int
    set_number: int = Field(ge=1, le=50)
    load_kg: float = Field(ge=0, le=1000)
    reps: int | None = Field(default=None, ge=0, le=200)


class SetLogOut(ORMModel):
    id: int
    routine_exercise_id: int
    set_number: int
    load_kg: float
    reps: int | None
    updated_at: datetime


class LastPerformance(BaseModel):
    session_date: date
    best_load_kg: float
    reps: int | None = None


class PlayerRoutineExercise(BaseModel):
    id: int
    position: int
    sets: int
    target_reps: int | None
    rest_seconds: int | None
    notes: str | None
    exercise: ExerciseOut
    logs: list[SetLogOut] = []
    last_performance: LastPerformance | None = None


class PlayerRoutine(BaseModel):
    id: int
    name: str
    session_date: date
    notes: str | None
    items: list[PlayerRoutineExercise] = []


class PlayerProgressRow(BaseModel):
    player_id: int
    player_name: str
    logged_sets: int
    total_sets: int


class RoutineProgress(BaseModel):
    routine: RoutineSummary
    rows: list[PlayerProgressRow] = []


Token.model_rebuild()
