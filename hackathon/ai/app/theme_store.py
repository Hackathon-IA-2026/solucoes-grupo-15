from typing import Protocol, Optional, List
from .models import ProcessClassification, TemaTaxonomy

class ProcessThemeClassifier(Protocol):
    def get_theme(self, tipo_processo: str) -> Optional[ProcessClassification]:
        ...

    def list_themes(self) -> List[TemaTaxonomy]:
        ...

    def get_types_by_theme(self, tema_id: str) -> List[str]:
        ...
