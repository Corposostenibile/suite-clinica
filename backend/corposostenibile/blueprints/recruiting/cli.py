"""
CLI commands for Recruiting module
"""

import click
from flask.cli import AppGroup
from flask import current_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    JobOffer, JobApplication, RecruitingKanban,
    OnboardingTemplate, Department,
    JobOfferStatusEnum, ApplicationStatusEnum
)
from datetime import datetime, timedelta

recruiting_cli = AppGroup('recruiting', help='Recruiting management commands')


@recruiting_cli.command('init')
def init_recruiting():
    """Initialize recruiting module with default data."""
    click.echo("Initializing recruiting module...")
    
    # Create default kanban if not exists
    default_kanban = RecruitingKanban.query.filter_by(is_default=True).first()
    if not default_kanban:
        default_kanban = RecruitingKanban.get_default()
        click.echo(f"✓ Created default kanban: {default_kanban.name}")
    else:
        click.echo(f"✓ Default kanban exists: {default_kanban.name}")
    
    # Create sample onboarding templates
    departments = Department.query.all()
    for dept in departments[:3]:  # Create for first 3 departments
        template = OnboardingTemplate.query.filter_by(
            department_id=dept.id
        ).first()
        
        if not template:
            template = OnboardingTemplate(
                name=f"Onboarding {dept.name}",
                department_id=dept.id,
                description=f"Template di onboarding standard per {dept.name}",
                duration_days=30,
                is_active=True
            )
            db.session.add(template)
            click.echo(f"✓ Created onboarding template for {dept.name}")
    
    db.session.commit()
    click.echo("Recruiting module initialized successfully!")


@recruiting_cli.command('stats')
def show_stats():
    """Show recruiting statistics."""
    click.echo("\n" + "="*60)
    click.echo("RECRUITING STATISTICS")
    click.echo("="*60)
    
    # Job offers
    total_offers = JobOffer.query.count()
    active_offers = JobOffer.query.filter_by(status=JobOfferStatusEnum.published).count()
    
    click.echo(f"\n📋 JOB OFFERS:")
    click.echo(f"   Total: {total_offers}")
    click.echo(f"   Active: {active_offers}")
    click.echo(f"   Draft: {JobOffer.query.filter_by(status=JobOfferStatusEnum.draft).count()}")
    click.echo(f"   Closed: {JobOffer.query.filter_by(status=JobOfferStatusEnum.closed).count()}")
    
    # Applications
    total_apps = JobApplication.query.count()
    
    click.echo(f"\n📝 APPLICATIONS:")
    click.echo(f"   Total: {total_apps}")
    click.echo(f"   New: {JobApplication.query.filter_by(status=ApplicationStatusEnum.new).count()}")
    click.echo(f"   In Review: {JobApplication.query.filter_by(status=ApplicationStatusEnum.reviewed).count()}")
    click.echo(f"   Hired: {JobApplication.query.filter_by(status=ApplicationStatusEnum.hired).count()}")
    click.echo(f"   Rejected: {JobApplication.query.filter_by(status=ApplicationStatusEnum.rejected).count()}")
    
    # Source distribution
    click.echo(f"\n📊 BY SOURCE:")
    from sqlalchemy import func
    sources = db.session.query(
        JobApplication.source,
        func.count(JobApplication.id).label('count')
    ).group_by(JobApplication.source).all()
    
    for source in sources:
        source_name = source.source.value if source.source else 'direct'
        click.echo(f"   {source_name}: {source.count}")
    
    # Conversion rate
    hired = JobApplication.query.filter_by(status=ApplicationStatusEnum.hired).count()
    if total_apps > 0:
        conversion = (hired / total_apps) * 100
        click.echo(f"\n✅ CONVERSION RATE: {conversion:.2f}%")
    
    click.echo("\n" + "="*60)


@recruiting_cli.command('cleanup')
@click.option('--days', default=90, help='Delete draft offers older than X days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
def cleanup_old_drafts(days, dry_run):
    """Clean up old draft job offers."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_drafts = JobOffer.query.filter(
        JobOffer.status == JobOfferStatusEnum.draft,
        JobOffer.created_at < cutoff_date
    ).all()
    
    if not old_drafts:
        click.echo("No old drafts to clean up.")
        return
    
    click.echo(f"Found {len(old_drafts)} draft offers older than {days} days:")
    
    for offer in old_drafts:
        click.echo(f"  - {offer.title} (created: {offer.created_at.date()})")
    
    if dry_run:
        click.echo("\n[DRY RUN] No offers were deleted.")
    else:
        if click.confirm(f"\nDelete {len(old_drafts)} old draft offers?"):
            for offer in old_drafts:
                db.session.delete(offer)
            db.session.commit()
            click.echo(f"✓ Deleted {len(old_drafts)} old draft offers.")
        else:
            click.echo("Cleanup cancelled.")


@recruiting_cli.command('auto-reject')
@click.option('--days', default=30, help='Auto-reject applications older than X days')
@click.option('--dry-run', is_flag=True, help='Show what would be rejected without rejecting')
def auto_reject_old(days, dry_run):
    """Auto-reject old applications that haven't been reviewed."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_applications = JobApplication.query.filter(
        JobApplication.status == ApplicationStatusEnum.new,
        JobApplication.created_at < cutoff_date
    ).all()
    
    if not old_applications:
        click.echo("No old applications to auto-reject.")
        return
    
    click.echo(f"Found {len(old_applications)} applications older than {days} days:")
    
    for app in old_applications[:10]:  # Show first 10
        click.echo(f"  - {app.full_name} for {app.job_offer.title if app.job_offer else 'Unknown'}")
    
    if len(old_applications) > 10:
        click.echo(f"  ... and {len(old_applications) - 10} more")
    
    if dry_run:
        click.echo("\n[DRY RUN] No applications were rejected.")
    else:
        if click.confirm(f"\nAuto-reject {len(old_applications)} old applications?"):
            for app in old_applications:
                app.status = ApplicationStatusEnum.rejected
                app.rejection_reason = f"Auto-rejected after {days} days without review"
            db.session.commit()
            click.echo(f"✓ Rejected {len(old_applications)} old applications.")
        else:
            click.echo("Auto-reject cancelled.")


@recruiting_cli.command('create-sample')
@click.option('--count', default=1, help='Number of sample job offers to create')
def create_sample_offers(count):
    """Create sample job offers for testing."""
    from faker import Faker
    fake = Faker('it_IT')
    
    departments = Department.query.all()
    if not departments:
        click.echo("No departments found. Please create departments first.")
        return
    
    kanban = RecruitingKanban.get_default()
    
    job_titles = [
        'Software Developer',
        'Frontend Developer',
        'Backend Developer',
        'DevOps Engineer',
        'Data Scientist',
        'Product Manager',
        'UX Designer',
        'Marketing Manager',
        'Sales Representative',
        'HR Specialist'
    ]
    
    created = 0
    for i in range(count):
        import random
        
        offer = JobOffer(
            title=random.choice(job_titles),
            description=fake.text(max_nb_chars=500),
            requirements=fake.text(max_nb_chars=300),
            benefits="Smart working, Buoni pasto, Formazione continua",
            salary_range="30k-50k EUR",
            location=fake.city(),
            employment_type=random.choice(['full-time', 'part-time', 'contract']),
            department_id=random.choice(departments).id,
            what_we_search="esperienza, competenze tecniche, problem solving",
            form_weight=50,
            cv_weight=50,
            kanban_id=kanban.id,
            status=JobOfferStatusEnum.draft
        )
        
        offer.generate_public_links()
        
        # Add sample questions
        from corposostenibile.models import JobQuestion, QuestionTypeEnum
        
        questions = [
            JobQuestion(
                question_text="Perché vuoi lavorare con noi?",
                question_type=QuestionTypeEnum.textarea,
                is_required=True,
                weight=30,
                order=0
            ),
            JobQuestion(
                question_text="Anni di esperienza",
                question_type=QuestionTypeEnum.number,
                expected_min=2,
                expected_max=10,
                is_required=True,
                weight=30,
                order=1
            ),
            JobQuestion(
                question_text="Disponibilità immediata?",
                question_type=QuestionTypeEnum.yes_no,
                expected_answer="si",
                is_required=True,
                weight=20,
                order=2
            ),
            JobQuestion(
                question_text="Competenze principali",
                question_type=QuestionTypeEnum.checkbox,
                options=["Python", "JavaScript", "SQL", "Docker", "Git"],
                expected_options=["Python", "Git"],
                is_required=False,
                weight=20,
                order=3
            )
        ]
        
        for q in questions:
            offer.questions.append(q)
        
        db.session.add(offer)
        created += 1
        
        click.echo(f"✓ Created offer: {offer.title}")
    
    db.session.commit()
    click.echo(f"\nSuccessfully created {created} sample job offers!")


@recruiting_cli.command('export')
@click.argument('offer_id', type=int)
@click.option('--format', type=click.Choice(['csv', 'excel']), default='csv')
@click.option('--output', help='Output file path')
def export_applications(offer_id, format, output):
    """Export applications for a job offer."""
    offer = JobOffer.query.get(offer_id)
    if not offer:
        click.echo(f"Job offer {offer_id} not found.")
        return
    
    applications = offer.applications.all()
    
    if not applications:
        click.echo(f"No applications for '{offer.title}'")
        return
    
    import pandas as pd
    
    # Prepare data
    data = []
    for app in applications:
        row = {
            'ID': app.id,
            'Nome': app.first_name,
            'Cognome': app.last_name,
            'Email': app.email,
            'Telefono': app.phone or '',
            'LinkedIn': app.linkedin_profile or '',
            'Fonte': app.source.value if app.source else 'direct',
            'Stato': app.status.value if app.status else 'new',
            'Score Form': app.form_score or 0,
            'Score CV': app.cv_score or 0,
            'Score Totale': app.total_score or 0,
            'Data Candidatura': app.created_at.strftime('%Y-%m-%d %H:%M')
        }
        
        # Add question answers
        for answer in app.answers:
            if answer.question:
                col_name = f"D: {answer.question.question_text[:30]}"
                row[col_name] = answer.answer_text or str(answer.answer_json)
        
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Generate output filename if not specified
    if not output:
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = "".join(c for c in offer.title if c.isalnum() or c in (' ', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:30]
        
        if format == 'excel':
            output = f"applications_{safe_title}_{timestamp}.xlsx"
        else:
            output = f"applications_{safe_title}_{timestamp}.csv"
    
    # Export
    if format == 'excel':
        df.to_excel(output, index=False)
    else:
        df.to_csv(output, index=False)
    
    click.echo(f"✓ Exported {len(applications)} applications to {output}")


@recruiting_cli.command('fix-kanban-stages')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without applying changes')
def fix_kanban_stages(dry_run):
    """Fix applications without kanban stage assigned."""
    from corposostenibile.models import KanbanStage, ApplicationStageHistory

    click.echo("\n" + "="*80)
    click.echo("🔧 FIX KANBAN STAGES - Assign missing stages to applications")
    click.echo("="*80 + "\n")

    # Find applications without stage
    apps_without_stage = JobApplication.query.filter_by(kanban_stage_id=None).all()

    if not apps_without_stage:
        click.secho("✅ All applications already have a kanban stage assigned!", fg='green')
        return

    click.echo(f"📊 Found {len(apps_without_stage)} applications without kanban stage\n")

    fixed_count = 0
    skipped_count = 0
    error_count = 0

    for i, application in enumerate(apps_without_stage, 1):
        job_offer = application.job_offer

        click.echo(f"[{i}/{len(apps_without_stage)}] {application.full_name}")
        click.echo(f"  Offer: {job_offer.title[:50]}...")
        click.echo(f"  Offer ID: {job_offer.id}")

        # Check if offer has kanban
        if not job_offer.kanban_id:
            click.secho(f"  ⚠️  SKIP: Offer has no kanban assigned", fg='yellow')
            skipped_count += 1
            continue

        kanban = job_offer.kanban
        click.echo(f"  Kanban: {kanban.name} (ID: {kanban.id})")

        # Find first active stage (lowest order)
        first_stage = min(
            [s for s in kanban.stages if s.is_active],
            key=lambda s: s.order,
            default=None
        )

        if not first_stage:
            click.secho(f"  ❌ ERROR: No active stage found in kanban!", fg='red')
            error_count += 1
            continue

        click.echo(f"  → First stage: {first_stage.name} (ID: {first_stage.id}, Order: {first_stage.order})")

        if not dry_run:
            try:
                # Assign stage
                application.kanban_stage_id = first_stage.id

                # Calculate kanban_order (last in column)
                max_order = db.session.query(db.func.max(JobApplication.kanban_order)).filter_by(
                    kanban_stage_id=first_stage.id
                ).scalar() or -1
                application.kanban_order = max_order + 1

                click.echo(f"  → Kanban order: {application.kanban_order}")

                # Create stage history entry
                history = ApplicationStageHistory(
                    application_id=application.id,
                    stage_id=first_stage.id,
                    previous_stage_id=None,
                    entered_at=application.created_at,
                    exited_at=None,
                    duration_seconds=None,
                    changed_by_id=None,
                    notes="Auto-assigned initial stage (CLI fix)"
                )
                db.session.add(history)

                # CRITICAL: Flush immediately to write to DB
                db.session.flush()

                click.secho(f"  ✅ FIXED", fg='green')
                fixed_count += 1

            except Exception as e:
                click.secho(f"  ❌ ERROR: {str(e)}", fg='red')
                error_count += 1
                db.session.rollback()
        else:
            click.secho(f"  ✓ Would fix (dry-run)", fg='cyan')
            fixed_count += 1

        click.echo()

    # Commit all changes
    if not dry_run and fixed_count > 0:
        click.echo("💾 Committing changes to database...")
        try:
            db.session.commit()
            click.secho("✅ COMMIT SUCCESSFUL!", fg='green', bold=True)

            # Verify changes were saved
            click.echo("\n🔍 Verifying changes...")
            remaining = JobApplication.query.filter_by(kanban_stage_id=None).count()
            click.echo(f"Applications still without stage: {remaining}")

            if remaining == 0:
                click.secho("\n🎉 SUCCESS! All applications now have a kanban stage!", fg='green', bold=True)
            else:
                click.secho(f"\n⚠️  WARNING: {remaining} applications still without stage", fg='yellow')

        except Exception as e:
            click.secho(f"❌ COMMIT FAILED: {str(e)}", fg='red', bold=True)
            db.session.rollback()
            click.echo("🔄 Changes rolled back")
            return

    # Summary
    click.echo("\n" + "="*80)
    click.echo("📊 SUMMARY")
    click.echo("="*80)
    click.secho(f"✅ Fixed:   {fixed_count}", fg='green')
    click.secho(f"⚠️  Skipped: {skipped_count}", fg='yellow')
    click.secho(f"❌ Errors:  {error_count}", fg='red')
    click.echo(f"📝 Total:   {len(apps_without_stage)}")

    if dry_run:
        click.echo("\n[DRY RUN] No changes were applied to the database.")
        click.echo("Run without --dry-run to apply changes.")

    click.echo()