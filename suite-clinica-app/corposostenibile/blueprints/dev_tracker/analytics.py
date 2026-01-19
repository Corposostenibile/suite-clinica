"""Analytics and statistics for Dev Tracker"""
from datetime import datetime, timedelta, date
from sqlalchemy import func, distinct
from corposostenibile.extensions import db
from corposostenibile.models import (
    DevWorkLog, DevCommit, DevCodeReview, DevSprint,
    DevSprintIntervention, BlueprintIntervention, User,
    WorkTypeEnum, CodeReviewStatusEnum, SprintStatusEnum
)


def get_developer_stats(user_id, days=30):
    """
    Statistiche per singolo developer.

    Returns:
        dict con total_hours, total_commits, total_interventions, etc.
    """
    start_date = date.today() - timedelta(days=days)

    # Ore lavorate
    total_hours = db.session.query(func.sum(DevWorkLog.hours_worked)).filter(
        DevWorkLog.user_id == user_id,
        DevWorkLog.date >= start_date
    ).scalar() or 0

    # Ore per tipo di lavoro
    hours_by_type = db.session.query(
        DevWorkLog.work_type,
        func.sum(DevWorkLog.hours_worked)
    ).filter(
        DevWorkLog.user_id == user_id,
        DevWorkLog.date >= start_date
    ).group_by(DevWorkLog.work_type).all()

    hours_breakdown = {wt.value: 0 for wt in WorkTypeEnum}
    for work_type, hours in hours_by_type:
        hours_breakdown[work_type.value] = float(hours or 0)

    # Commits
    total_commits = db.session.query(func.count(DevCommit.id)).filter(
        DevCommit.user_id == user_id,
        DevCommit.committed_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    commits_stats = db.session.query(
        func.sum(DevCommit.additions),
        func.sum(DevCommit.deletions),
        func.sum(DevCommit.files_changed)
    ).filter(
        DevCommit.user_id == user_id,
        DevCommit.committed_at >= datetime.combine(start_date, datetime.min.time())
    ).first()

    # Interventions attivi e completati
    active_interventions = db.session.query(func.count(BlueprintIntervention.id)).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        BlueprintIntervention.status.in_(['todo', 'in_progress'])
    ).scalar() or 0

    completed_interventions = db.session.query(func.count(BlueprintIntervention.id)).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        BlueprintIntervention.status == 'done',
        BlueprintIntervention.completed_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    # Code reviews
    reviews_given = db.session.query(func.count(DevCodeReview.id)).filter(
        DevCodeReview.reviewer_id == user_id,
        DevCodeReview.created_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    reviews_received = db.session.query(func.count(DevCodeReview.id)).filter(
        DevCodeReview.author_id == user_id,
        DevCodeReview.created_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    # Media ore/giorno
    days_worked = db.session.query(func.count(distinct(DevWorkLog.date))).filter(
        DevWorkLog.user_id == user_id,
        DevWorkLog.date >= start_date
    ).scalar() or 1

    avg_hours_per_day = float(total_hours) / days_worked if days_worked > 0 else 0

    # Avg completion time (interventions completati)
    completed = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        BlueprintIntervention.status == 'done',
        BlueprintIntervention.completed_at >= datetime.combine(start_date, datetime.min.time()),
        BlueprintIntervention.start_date.isnot(None)
    ).all()

    completion_times = []
    for intervention in completed:
        if intervention.start_date and intervention.completed_at:
            delta = intervention.completed_at.date() - intervention.start_date
            completion_times.append(delta.days)

    avg_completion_days = sum(completion_times) / len(completion_times) if completion_times else 0

    return {
        'total_hours': float(total_hours),
        'hours_breakdown': hours_breakdown,
        'avg_hours_per_day': round(avg_hours_per_day, 1),
        'days_worked': days_worked,
        'total_commits': total_commits,
        'additions': int(commits_stats[0] or 0),
        'deletions': int(commits_stats[1] or 0),
        'files_changed': int(commits_stats[2] or 0),
        'active_interventions': active_interventions,
        'completed_interventions': completed_interventions,
        'avg_completion_days': round(avg_completion_days, 1),
        'reviews_given': reviews_given,
        'reviews_received': reviews_received,
    }


def get_team_stats(department_id, days=30):
    """
    Statistiche per team (department).

    Returns:
        dict con team stats
    """
    start_date = date.today() - timedelta(days=days)

    # Team members
    team_members = User.query.filter_by(department_id=department_id, is_active=True).all()
    team_ids = [u.id for u in team_members]

    if not team_ids:
        return {
            'total_members': 0,
            'total_hours': 0,
            'total_commits': 0,
            'active_interventions': 0,
            'completed_interventions': 0,
            'pending_reviews': 0,
            'active_sprints': 0,
            'sprint_completion_rate': 0,
        }

    # Ore totali team
    total_hours = db.session.query(func.sum(DevWorkLog.hours_worked)).filter(
        DevWorkLog.user_id.in_(team_ids),
        DevWorkLog.date >= start_date
    ).scalar() or 0

    # Commits totali
    total_commits = db.session.query(func.count(DevCommit.id)).filter(
        DevCommit.user_id.in_(team_ids),
        DevCommit.committed_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    # Interventions attivi e completati
    active_interventions = db.session.query(func.count(BlueprintIntervention.id)).filter(
        BlueprintIntervention.assigned_to_id.in_(team_ids),
        BlueprintIntervention.status.in_(['todo', 'in_progress'])
    ).scalar() or 0

    completed_interventions = db.session.query(func.count(BlueprintIntervention.id)).filter(
        BlueprintIntervention.assigned_to_id.in_(team_ids),
        BlueprintIntervention.status == 'done',
        BlueprintIntervention.completed_at >= datetime.combine(start_date, datetime.min.time())
    ).scalar() or 0

    # Pending code reviews
    pending_reviews = db.session.query(func.count(DevCodeReview.id)).filter(
        DevCodeReview.reviewer_id.in_(team_ids),
        DevCodeReview.status == CodeReviewStatusEnum.pending
    ).scalar() or 0

    # Sprint attivi
    active_sprints = db.session.query(func.count(DevSprint.id)).filter(
        DevSprint.department_id == department_id,
        DevSprint.status == SprintStatusEnum.active
    ).scalar() or 0

    # Sprint completion rate (ultimo sprint completato)
    last_sprint = db.session.query(DevSprint).filter(
        DevSprint.department_id == department_id,
        DevSprint.status == SprintStatusEnum.completed
    ).order_by(DevSprint.end_date.desc()).first()

    sprint_completion_rate = 0
    if last_sprint and last_sprint.total_story_points > 0:
        sprint_completion_rate = (last_sprint.completed_story_points / last_sprint.total_story_points) * 100

    return {
        'total_members': len(team_members),
        'total_hours': float(total_hours),
        'total_commits': total_commits,
        'active_interventions': active_interventions,
        'completed_interventions': completed_interventions,
        'pending_reviews': pending_reviews,
        'active_sprints': active_sprints,
        'sprint_completion_rate': round(sprint_completion_rate, 1),
    }


def get_sprint_velocity(department_id, sprint_count=5):
    """
    Calcola velocity degli ultimi N sprint.

    Returns:
        list di dict [{sprint_name, story_points, completed_points, velocity}, ...]
    """
    sprints = db.session.query(DevSprint).filter(
        DevSprint.department_id == department_id,
        DevSprint.status.in_([SprintStatusEnum.completed, SprintStatusEnum.active])
    ).order_by(DevSprint.start_date.desc()).limit(sprint_count).all()

    velocity_data = []
    for sprint in reversed(sprints):  # Oldest first
        velocity_data.append({
            'sprint_name': sprint.name,
            'story_points': sprint.total_story_points or 0,
            'completed_points': sprint.completed_story_points or 0,
            'velocity': sprint.completed_story_points or 0,
            'completion_rate': sprint.progress_percentage,
        })

    return velocity_data


def get_workload_distribution(team_ids):
    """
    Distribuzione carico di lavoro per developers.

    Returns:
        list di dict [{user_id, user_name, active_interventions, total_story_points, hours_this_week}, ...]
    """
    from datetime import date, timedelta

    week_start = date.today() - timedelta(days=date.today().weekday())

    workload = []
    for user_id in team_ids:
        user = User.query.get(user_id)
        if not user:
            continue

        # Interventions attivi
        active_interventions = db.session.query(func.count(BlueprintIntervention.id)).filter(
            BlueprintIntervention.assigned_to_id == user_id,
            BlueprintIntervention.status.in_(['todo', 'in_progress'])
        ).scalar() or 0

        # Story points totali (da sprint attivi)
        total_story_points = db.session.query(func.sum(DevSprintIntervention.story_points)).join(
            BlueprintIntervention
        ).join(DevSprint).filter(
            BlueprintIntervention.assigned_to_id == user_id,
            DevSprint.status == SprintStatusEnum.active
        ).scalar() or 0

        # Ore questa settimana
        hours_this_week = db.session.query(func.sum(DevWorkLog.hours_worked)).filter(
            DevWorkLog.user_id == user_id,
            DevWorkLog.date >= week_start
        ).scalar() or 0

        workload.append({
            'user_id': user_id,
            'user_name': f"{user.first_name} {user.last_name}",
            'avatar_path': user.avatar_path,
            'active_interventions': active_interventions,
            'total_story_points': int(total_story_points),
            'hours_this_week': float(hours_this_week),
        })

    # Ordina per carico (interventions + story_points)
    workload.sort(key=lambda x: x['active_interventions'] + (x['total_story_points'] / 10), reverse=True)

    return workload


def get_recent_activity(user_id, limit=10):
    """
    Attività recenti per developer.

    Returns:
        list di dict con work_logs, commits, reviews
    """
    activity = []

    # Work logs
    work_logs = db.session.query(DevWorkLog).filter(
        DevWorkLog.user_id == user_id
    ).order_by(DevWorkLog.date.desc()).limit(limit).all()

    for log in work_logs:
        activity.append({
            'type': 'worklog',
            'date': log.date,
            'description': f"{log.hours_worked}h - {log.work_type.value}: {log.description or ''}",
            'icon': 'clock',
        })

    # Commits
    commits = db.session.query(DevCommit).filter(
        DevCommit.user_id == user_id
    ).order_by(DevCommit.committed_at.desc()).limit(limit).all()

    for commit in commits:
        activity.append({
            'type': 'commit',
            'date': commit.committed_at.date() if commit.committed_at else date.today(),
            'description': f"{commit.commit_hash[:7]}: {commit.commit_message[:50]}",
            'icon': 'code-branch',
        })

    # Code reviews
    reviews = db.session.query(DevCodeReview).filter(
        DevCodeReview.reviewer_id == user_id
    ).order_by(DevCodeReview.created_at.desc()).limit(limit).all()

    for review in reviews:
        activity.append({
            'type': 'review',
            'date': review.created_at.date(),
            'description': f"Review #{review.id} - {review.status.value}",
            'icon': 'eye',
        })

    # Ordina per data
    activity.sort(key=lambda x: x['date'], reverse=True)

    return activity[:limit]
