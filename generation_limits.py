"""Signal incomplete provider output without presenting it as a finished reply."""


class GenerationBudgetError(RuntimeError):
    def __init__(self, text):
        super().__init__("Model output exhausted its token budget")
        self.partial_text = text
