from simple_spaced_repetition import review

def update_review_schedule(current_interval, performance):
    """Uses SSR library to calculate the next review interval."""
    new_interval = review(current_interval, performance)
    return new_interval