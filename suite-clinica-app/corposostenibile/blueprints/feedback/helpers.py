"""
Feedback helpers for department-based access control.
"""

from flask_login import current_user


def is_in_department(department_keywords) -> bool:
    """Check if user is member of a department matching keywords."""
    if not current_user or not current_user.is_authenticated:
        return False
    
    # Check single department
    if hasattr(current_user, 'department') and current_user.department:
        dept_name = current_user.department.name.lower()
        for keyword in department_keywords:
            if keyword in dept_name:
                return True
    
    # Check multiple departments
    if hasattr(current_user, 'departments') and current_user.departments:
        for dept in current_user.departments:
            dept_name = dept.name.lower()
            for keyword in department_keywords:
                if keyword in dept_name:
                    return True
    
    return False


def is_department_head(department_keywords) -> bool:
    """Check if user is head of a department matching keywords."""
    if not current_user or not current_user.is_authenticated:
        return False

    if hasattr(current_user, 'departments_led') and current_user.departments_led:
        for dept in current_user.departments_led:
            dept_name = dept.name.lower()
            for keyword in department_keywords:
                if keyword in dept_name:
                    return True

    return False


def is_team_leader_in_department(department_keywords) -> bool:
    """Check if user is a team leader in a department matching keywords."""
    if not current_user or not current_user.is_authenticated:
        return False

    if hasattr(current_user, 'teams_led') and current_user.teams_led:
        for team in current_user.teams_led:
            if team.department:
                dept_name = team.department.name.lower()
                for keyword in department_keywords:
                    if keyword in dept_name:
                        return True

    return False


def get_led_team_member_ids(department_keywords) -> list:
    """
    Get IDs of all members in teams led by current user in matching departments.
    Returns list of user IDs (including the team leader themselves).
    """
    if not current_user or not current_user.is_authenticated:
        return []

    member_ids = set()

    if hasattr(current_user, 'teams_led') and current_user.teams_led:
        for team in current_user.teams_led:
            if team.department:
                dept_name = team.department.name.lower()
                for keyword in department_keywords:
                    if keyword in dept_name:
                        # Add all team members
                        for member in team.members:
                            if member.is_active:
                                member_ids.add(member.id)
                        # Add team leader (current user)
                        member_ids.add(current_user.id)
                        break

    return list(member_ids)


def can_access_nutrition_feedback() -> bool:
    """Check if current user can access nutrition feedback."""
    if not current_user or not current_user.is_authenticated:
        return False

    if current_user.is_admin or current_user.id in [4, 22, 49, 95]:
        return True

    # Team leaders, members and heads of Nutrizione and Customer Success departments can access
    return (is_team_leader_in_department(['nutrizion']) or
            is_in_department(['nutrizion']) or
            is_department_head(['nutrizion', 'customer success']))


def can_access_psychology_feedback() -> bool:
    """Check if current user can access psychology feedback."""
    if not current_user or not current_user.is_authenticated:
        return False

    if current_user.is_admin or current_user.id in [5, 95]:
        return True

    # Team leaders, members and heads of Psicologia and Customer Success departments can access
    return (is_team_leader_in_department(['psicolog']) or
            is_in_department(['psicolog']) or
            is_department_head(['psicolog', 'customer success']))


def can_access_coach_feedback() -> bool:
    """Check if current user can access coach feedback."""
    if not current_user or not current_user.is_authenticated:
        return False

    if current_user.is_admin or current_user.id in [2, 95]:
        return True

    # Members and heads of Coach/Sport and Customer Success departments can access
    return is_in_department(['coach', 'sport']) or is_department_head(['coach', 'sport', 'customer success'])


def can_access_health_manager_feedback() -> bool:
    """Check if current user can access health manager feedback."""
    if not current_user or not current_user.is_authenticated:
        return False

    if current_user.is_admin or current_user.id == 95:
        return True

    # Members and heads of Health Manager department (dipartimento 13) and Customer Success can access
    return is_in_department(['health manager']) or is_department_head(['health manager', 'customer success'])


def get_user_feedback_filter():
    """
    Returns filter for feedback based on user's role.
    - Admin: No filter (sees all)
    - User ID 2, 4, 5, 22, 49, 95: No filter (sees all like admin)
    - Team Leader (Nutrizione/Psicologia): Filter by team members
    - Department Head (other depts): Filter by department
    - Department Member: Filter by their own feedback only
    """
    if current_user.is_admin or current_user.id in [2, 4, 5, 22, 49, 95]:
        return None  # No filter

    # Customer Success heads see all feedback
    if is_department_head(['customer success']):
        return None

    # Team Leaders for Nutrizione - see their team's feedback
    if is_team_leader_in_department(['nutrizion']):
        team_member_ids = get_led_team_member_ids(['nutrizion'])
        return {'type': 'team', 'team_member_ids': team_member_ids, 'department': 'nutrizionista'}

    # Team Leaders for Psicologia - see their team's feedback
    if is_team_leader_in_department(['psicolog']):
        team_member_ids = get_led_team_member_ids(['psicolog'])
        return {'type': 'team', 'team_member_ids': team_member_ids, 'department': 'psicologa'}

    # Department heads for other departments (Coach, etc.)
    if is_department_head(['coach', 'sport']):
        return {'type': 'department', 'department': 'coach'}

    # Regular department member - only see their own feedback
    if is_in_department(['nutrizion', 'psicolog', 'coach', 'sport']):
        return {'type': 'personal', 'user_id': current_user.id}

    return {'type': 'none'}  # No access 