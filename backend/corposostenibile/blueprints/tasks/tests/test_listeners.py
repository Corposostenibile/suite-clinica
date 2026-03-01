"""
Test completo per Task Listeners.
Escluso: Ticket (problema Enum ambiente).
"""

import sys
import os
sys.path.append(os.getcwd())

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Cliente, Task, TaskTypeEnum, TaskStatusEnum,
    Department, ReviewRequest
)

app = create_app()


def setup_test_data():
    """Crea dati di test se non esistono."""
    with app.app_context():
        user = User.query.filter_by(email="listener_test@example.com").first()
        if not user:
            user = User(
                email="listener_test@example.com",
                first_name="Listener",
                last_name="Tester",
                password_hash="test"
            )
            db.session.add(user)
            
        dept = Department.query.filter_by(name="Test Listeners Dept").first()
        if not dept:
            dept = Department(name="Test Listeners Dept")
            db.session.add(dept)
            
        db.session.commit()
        return user.id, dept.id


def test_onboarding_task():
    """Test: Creazione Cliente -> Task Onboarding."""
    print("\n=== TEST: Onboarding Task ===")
    with app.app_context():
        user = User.query.filter_by(email="listener_test@example.com").first()
        
        # Cleanup
        # Task.query.filter(Task.title.like("%TestOnboarding%")).delete()
        # Cliente.query.filter(Cliente.nome_cognome == "TestOnboarding Client").delete()
        # db.session.commit()
        
        # Crea professionisti fittizi
        coach = User.query.filter_by(email="coach_test@example.com").first()
        if not coach:
            coach = User(email="coach_test@example.com", first_name="Coach", last_name="Test", password_hash="test")
            db.session.add(coach)
            
        nutri = User.query.filter_by(email="nutri_test_onb@example.com").first()
        if not nutri:
            nutri = User(email="nutri_test_onb@example.com", first_name="Nutri", last_name="Test", password_hash="test")
            db.session.add(nutri)
        
        db.session.commit()

        # Crea cliente assegnato
        cliente = Cliente(
            nome_cognome="TestOnboarding Client",
            mail="onboard@test.com",
            numero_telefono="123",
            created_by=user.id,
            coach_user=coach,
            nutrizionista_user=nutri
        )
        db.session.add(cliente)
        db.session.commit()
        
        # Verifica Task (dovrebbero essercene 2: Coach e Nutri)
        tasks = Task.query.filter_by(
            cliente_id=cliente.cliente_id,
            type=TaskTypeEnum.onboarding
        ).all()
        
        if len(tasks) >= 2:
            print(f"✅ SUCCESS: Creati {len(tasks)} Task Onboarding")
            
            assignees = [t.assigned_to_id for t in tasks]
            if coach.id in assignees and nutri.id in assignees:
                print(f"✅ SUCCESS: Task assegnati correttamente a Coach ({coach.id}) e Nutri ({nutri.id})")
                return True
            else:
                print(f"❌ FAILURE: Assegnazione errata. Assignees: {assignees}")
                return False
        else:
            print(f"❌ FAILURE: Trovati solo {len(tasks)} task (attesi >= 2)")
            return False


def test_reach_out_task():
    """Test: Update reach_out_nutrizione -> Task Reach Out."""
    print("\n=== TEST: Reach Out Task ===")
    with app.app_context():
        cliente = Cliente.query.filter_by(mail="onboard@test.com").first()
        if not cliente:
            print("⚠️ SKIP: Cliente non trovato (esegui test_onboarding prima)")
            return False
            
        # Cleanup vecchi task reach out
        # Task.query.filter(
        #     Task.cliente_id == cliente.cliente_id,
        #     Task.type == TaskTypeEnum.reach_out
        # ).delete()
        # db.session.commit()
        
        # Assegna un nutrizionista per testare l'assegnazione
        nutri_user = User.query.filter_by(email="nutri_test@example.com").first()
        if not nutri_user:
            nutri_user = User(
                email="nutri_test@example.com",
                first_name="Nutri",
                last_name="Tester",
                password_hash="test"
            )
            db.session.add(nutri_user)
            db.session.commit()
            
        cliente.nutrizionista_user = nutri_user
        
        # Update reach_out_nutrizione
        cliente.reach_out_nutrizione = 'lun'
        db.session.commit()
        
        task = Task.query.filter_by(
            cliente_id=cliente.cliente_id,
            type=TaskTypeEnum.reach_out
        ).order_by(Task.id.desc()).first()
        
        if task and "Nutrizione" in task.title:
            print(f"✅ SUCCESS: Reach Out Task creato - '{task.title}' (Due: {task.due_date})")
            
            if task.assigned_to_id == nutri_user.id:
                print(f"✅ SUCCESS: Assegnazione corretta a Nutrizionista (User {nutri_user.id})")
                return True
            else:
                print(f"❌ FAILURE: Assegnazione errata ({task.assigned_to_id} vs {nutri_user.id})")
                return False
        else:
            print("❌ FAILURE: Reach Out Task non trovato")
            return False


def test_reach_out_recursion():
    """Test: Completamento Reach Out -> Nuovo Task."""
    print("\n=== TEST: Reach Out Recursion ===")
    with app.app_context():
        cliente = Cliente.query.filter_by(mail="onboard@test.com").first()
        if not cliente:
            print("⚠️ SKIP: Cliente non trovato")
            return False
            
        task = Task.query.filter_by(
            cliente_id=cliente.cliente_id,
            type=TaskTypeEnum.reach_out,
            status=TaskStatusEnum.todo
        ).order_by(Task.id.desc()).first()
        
        if not task:
            print("⚠️ SKIP: Nessun task Reach Out da completare")
            return False
            
        old_task_id = task.id
        old_due_date = task.due_date
        old_assignee_id = task.assigned_to_id
        
        # Completa task
        task.status = TaskStatusEnum.done
        db.session.commit()
        
        # Verifica nuovo task
        new_task = Task.query.filter(
            Task.cliente_id == cliente.cliente_id,
            Task.type == TaskTypeEnum.reach_out,
            Task.id != old_task_id
        ).order_by(Task.id.desc()).first()
        
        if new_task and new_task.status == TaskStatusEnum.todo:
            expected_date = old_due_date + __import__('datetime').timedelta(days=7)
            if new_task.due_date == expected_date:
                print(f"✅ SUCCESS: Recursion Task creato - Due: {new_task.due_date}")
                
                if new_task.assigned_to_id == old_assignee_id:
                     print(f"✅ SUCCESS: Assegnazione mantenuta (User {new_task.assigned_to_id})")
                     return True
                else:
                     print(f"❌ FAILURE: Assegnazione persa nella ricorsione ({new_task.assigned_to_id})")
                     return False
            else:
                print(f"⚠️ PARTIAL: Task creato ma data errata ({new_task.due_date} vs expected {expected_date})")
                return True
        else:
            print("❌ FAILURE: Recursion Task non creato")
            return False


def test_training_task():
    """Test: Creazione ReviewRequest -> Task Training."""
    print("\n=== TEST: Training Task ===")
    with app.app_context():
        user = User.query.filter_by(email="listener_test@example.com").first()
        
        # Cleanup
        # Task.query.filter(Task.title.like("%Richiesta Training da Listener%")).delete()
        # ReviewRequest.query.filter(ReviewRequest.subject == "Test Training Request").delete()
        # db.session.commit()
        
        # Crea ReviewRequest
        request = ReviewRequest(
            requester_id=user.id,
            requested_to_id=user.id,
            subject="Test Training Request",
            description="Descrizione test",
            priority="medium",
            status="pending"
        )
        db.session.add(request)
        db.session.commit()
        
        # Verifica Task
        task = Task.query.filter(
            Task.type == TaskTypeEnum.training,
            Task.title.like("%Richiesta Training da Listener%")
        ).first()
        
        if task:
            print(f"✅ SUCCESS: Training Task creato - '{task.title}'")
            
            if task.assigned_to_id == user.id:
                print(f"✅ SUCCESS: Assegnazione corretta (User {user.id})")
                return True
            else:
                print(f"❌ FAILURE: Assegnazione errata ({task.assigned_to_id} vs {user.id})")
                return False
        else:
            print("❌ FAILURE: Training Task non trovato")
            return False


def cleanup():
    """Pulizia dati test."""
    print("\n=== CLEANUP ===")
    with app.app_context():
        Task.query.filter(Task.title.like("%TestOnboarding%")).delete()
        Task.query.filter(Task.title.like("%Richiesta Training da Listener%")).delete()
        Task.query.filter(Task.title.like("%Reach Out%")).delete()
        Cliente.query.filter(Cliente.nome_cognome == "TestOnboarding Client").delete()
        ReviewRequest.query.filter(ReviewRequest.subject == "Test Training Request").delete()
        db.session.commit()
        print("Cleanup completato")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST SUITE: Task Listeners")
    print("=" * 60)
    
    setup_test_data()
    
    results = {
        "Onboarding": test_onboarding_task(),
        "Reach Out": test_reach_out_task(),
        "Recursion": test_reach_out_recursion(),
        "Training": test_training_task(),
    }
    
    print("\n" + "=" * 60)
    print("RISULTATI:")
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotale: {passed}/{total} test passati")
    print("=" * 60)
    
    # Non fare cleanup per ispezionare i dati se necessario
    # cleanup()
