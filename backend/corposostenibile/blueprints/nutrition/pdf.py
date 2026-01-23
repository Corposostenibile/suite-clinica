"""
Generazione PDF per piani alimentari
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

from corposostenibile.models import MealPlan, MealPlanDay, MealTypeEnum


def create_meal_plan_pdf(meal_plan: MealPlan) -> str:
    """
    Genera PDF completo del piano alimentare.
    
    Args:
        meal_plan: piano alimentare da esportare
    
    Returns:
        Path del file PDF generato
    """
    # Crea file temporaneo
    pdf_dir = Path(tempfile.gettempdir()) / 'corposostenibile_pdfs'
    pdf_dir.mkdir(exist_ok=True)
    
    filename = f"piano_{meal_plan.cliente.cliente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = pdf_dir / filename
    
    # Crea documento
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )
    
    # Stili
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2E7D32'),
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name='SubTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#388E3C'),
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='InfoText',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY
    ))
    
    # Contenuto
    story = []
    
    # Logo (se presente)
    logo_path = current_app.config.get('COMPANY_LOGO_PATH')
    if logo_path and os.path.exists(logo_path):
        img = Image(logo_path, width=6*cm, height=2*cm)
        story.append(img)
        story.append(Spacer(1, 1*cm))
    
    # Titolo
    story.append(Paragraph("Piano Alimentare Personalizzato", styles['CustomTitle']))
    story.append(Spacer(1, 0.5*cm))
    
    # Info cliente
    info_data = [
        ['Cliente:', meal_plan.cliente.nome_cognome],
        ['Periodo:', f"{meal_plan.start_date.strftime('%d/%m/%Y')} - {meal_plan.end_date.strftime('%d/%m/%Y')}"],
        ['Nutrizionista:', meal_plan.created_by.full_name],
        ['Data creazione:', meal_plan.created_at.strftime('%d/%m/%Y')]
    ]
    
    info_table = Table(info_data, colWidths=[5*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONT', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 1*cm))
    
    # Obiettivi nutrizionali
    story.append(Paragraph("Obiettivi Nutrizionali Giornalieri", styles['SubTitle']))
    
    target_data = [
        ['Parametro', 'Target', 'Note'],
        ['Calorie', f"{int(meal_plan.target_calories)} kcal" if meal_plan.target_calories else 'N/D', ''],
        ['Proteine', f"{meal_plan.target_proteins:.1f} g" if meal_plan.target_proteins else 'N/D', ''],
        ['Carboidrati', f"{meal_plan.target_carbohydrates:.1f} g" if meal_plan.target_carbohydrates else 'N/D', ''],
        ['Grassi', f"{meal_plan.target_fats:.1f} g" if meal_plan.target_fats else 'N/D', '']
    ]
    
    target_table = Table(target_data, colWidths=[6*cm, 4*cm, 7*cm])
    target_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F5E9')),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
    ]))
    story.append(target_table)
    story.append(PageBreak())
    
    # Giorni del piano
    days = MealPlanDay.query.filter_by(
        meal_plan_id=meal_plan.id
    ).order_by(MealPlanDay.day_date).all()
    
    for day in days:
        # Intestazione giorno
        day_title = f"Giorno {day.day_number} - {day.day_date.strftime('%A %d/%m/%Y')}"
        story.append(Paragraph(day_title, styles['SubTitle']))
        
        # Tabella pasti del giorno
        day_data = [['Pasto', 'Alimenti', 'Quantità', 'Calorie', 'P', 'C', 'G']]
        
        day_totals = {
            'calories': 0,
            'proteins': 0,
            'carbs': 0,
            'fats': 0
        }
        
        # Ordine pasti
        meal_order = [
            MealTypeEnum.colazione,
            MealTypeEnum.spuntino_mattina,
            MealTypeEnum.pranzo,
            MealTypeEnum.spuntino_pomeriggio,
            MealTypeEnum.cena,
            MealTypeEnum.spuntino_sera
        ]
        
        for meal_type in meal_order:
            meal = next((m for m in day.meals if m.meal_type == meal_type.value), None)
            
            if meal:
                # Prima riga del pasto
                meal_name = meal_type.value.replace('_', ' ').title()
                if meal.name:
                    meal_name += f"\n{meal.name}"
                
                if meal.foods:
                    first_food = meal.foods[0]
                    food_name = first_food.food.name if first_food.food else first_food.recipe.name
                    
                    day_data.append([
                        meal_name,
                        food_name,
                        f"{first_food.quantity} {first_food.unit}",
                        f"{int(first_food.calories)}",
                        f"{first_food.proteins:.1f}",
                        f"{first_food.carbohydrates:.1f}",
                        f"{first_food.fats:.1f}"
                    ])
                    
                    # Altri alimenti dello stesso pasto
                    for food in meal.foods[1:]:
                        food_name = food.food.name if food.food else food.recipe.name
                        day_data.append([
                            "",
                            food_name,
                            f"{food.quantity} {food.unit}",
                            f"{int(food.calories)}",
                            f"{food.proteins:.1f}",
                            f"{food.carbohydrates:.1f}",
                            f"{food.fats:.1f}"
                        ])
                    
                    # Totali pasto
                    day_data.append([
                        "",
                        Paragraph("<b>Totale pasto</b>", styles['Normal']),
                        "",
                        f"{int(meal.total_calories)}",
                        f"{meal.total_proteins:.1f}",
                        f"{meal.total_carbohydrates:.1f}",
                        f"{meal.total_fats:.1f}"
                    ])
                    
                    day_totals['calories'] += meal.total_calories
                    day_totals['proteins'] += meal.total_proteins
                    day_totals['carbs'] += meal.total_carbohydrates
                    day_totals['fats'] += meal.total_fats
        
        # Riga totali giorno
        day_data.append([
            Paragraph("<b>TOTALE GIORNO</b>", styles['Normal']),
            "",
            "",
            f"{int(day_totals['calories'])}",
            f"{day_totals['proteins']:.1f}",
            f"{day_totals['carbs']:.1f}",
            f"{day_totals['fats']:.1f}"
        ])
        
        # Crea tabella
        col_widths = [4*cm, 6*cm, 2.5*cm, 1.5*cm, 1*cm, 1*cm, 1*cm]
        day_table = Table(day_data, colWidths=col_widths)
        day_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F5E9')),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#FFFDE7')),
            ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        # Aggiungi tabella alla storia mantenendola insieme
        story.append(KeepTogether([
            Paragraph(day_title, styles['SubTitle']),
            day_table,
            Spacer(1, 0.5*cm)
        ]))
        
        # Note del giorno
        if day.notes:
            story.append(Paragraph(f"Note: {day.notes}", styles['InfoText']))
            story.append(Spacer(1, 0.5*cm))
    
    # Note finali
    if meal_plan.notes:
        story.append(PageBreak())
        story.append(Paragraph("Note del Piano", styles['SubTitle']))
        story.append(Paragraph(meal_plan.notes, styles['InfoText']))
    
    # Footer
    story.append(Spacer(1, 2*cm))
    footer_text = f"Documento generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}"
    story.append(Paragraph(footer_text, styles['InfoText']))
    
    # Genera PDF
    doc.build(story)
    
    return str(pdf_path)


def create_shopping_list_pdf(shopping_list: dict, meal_plan: MealPlan) -> str:
    """
    Genera PDF della lista della spesa.
    
    Args:
        shopping_list: dizionario con lista spesa
        meal_plan: piano alimentare di riferimento
    
    Returns:
        Path del file PDF generato
    """
    pdf_dir = Path(tempfile.gettempdir()) / 'corposostenibile_pdfs'
    pdf_dir.mkdir(exist_ok=True)
    
    filename = f"spesa_{meal_plan.cliente.cliente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = pdf_dir / filename
    
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # Titolo
    story.append(Paragraph("Lista della Spesa", styles['Title']))
    story.append(Paragraph(
        f"Piano: {meal_plan.name} - Dal {meal_plan.start_date.strftime('%d/%m')} al {meal_plan.end_date.strftime('%d/%m')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 1*cm))
    
    # Lista per categoria
    for category, items in sorted(shopping_list.items()):
        story.append(Paragraph(category, styles['Heading2']))
        
        data = [['Alimento', 'Quantità']]
        for item_name, item_data in sorted(items.items()):
            quantity = item_data['quantity']
            unit = item_data['unit']
            
            # Converti grammi in kg se > 1000
            if unit == 'g' and quantity >= 1000:
                quantity = quantity / 1000
                unit = 'kg'
            
            data.append([item_name, f"{quantity:.0f} {unit}"])
        
        table = Table(data, colWidths=[12*cm, 4*cm])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.5*cm))
    
    doc.build(story)
    return str(pdf_path)