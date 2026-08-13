class AppException(Exception):
    """Base class for all application-specific errors."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class PalSpeciesNotFoundError(AppException):
    def __init__(self, species_name: str):
        super().__init__(
            message=f"Pal species '{species_name}' does not exist in the Paldeck.",
            status_code=400
        )

class PalInventoryNotFoundError(AppException):
    def __init__(self, pal_id: int):
        super().__init__(
            message=f"Pal with ID {pal_id} was not found in your inventory.",
            status_code=404
        )

class UserNotFoundError(AppException):
    def __init__(self, user_id: int):
        super().__init__(
            message=f"User with ID {user_id} does not exist.",
            status_code=404
        )

class NoBreedingCombinationsError(AppException):
    def __init__(self, target_species: str):
        super().__init__(
            message=f"No combinations in your current inventory can produce '{target_species}'.",
            status_code=404
        )

class PassiveSkillNotFoundError(AppException):
    def __init__(self, passive_name: str):
        super().__init__(
            message=f"Passive skill '{passive_name}' does not exist.",
            status_code=400
        )