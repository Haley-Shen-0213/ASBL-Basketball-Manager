# manage.py
from app import create_app
from app.services.league_service import LeagueService

app = create_app()

def manual_trigger():
    print("1. Trigger 00:00 (Day Change & Daily Schedule)")
    print("2. Trigger 19:00 (Match Execution)")
    choice = input("Select action: ")
    
    with app.app_context():
        if choice == '1':
            LeagueService.process_day_change_0000()
        elif choice == '2':
            LeagueService.process_match_execution_1900()
        else:
            print("Invalid")

if __name__ == '__main__':
    manual_trigger()
