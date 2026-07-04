import os

view_path = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\core\views.py"
template_path = r"c:\Users\PC HOME\OneDrive\Desktop\hadramout_events\hadramout_events_final\hadramout_events\templates\custom_admin\manager_dashboard.html"

# 1. Update core/views.py
with open(view_path, "r", encoding="utf-8") as f:
    views_content = f.read()

# Locate get_context_data inside CustomManagerDashboardView
old_context_block = """        context.update({
            'total_revenue': total_revenue,
            'total_fees': total_fees,
            'revenue_growth': round(float(revenue_growth), 1),
            'active_vouchers_count': active_vouchers_count,
            'exhausted_vouchers_count': exhausted_vouchers_count,
            'expired_vouchers_count': expired_vouchers_count,
            'total_doctors': total_doctors,
            'total_vendors': total_vendors,
            'total_transactions': total_transactions,
            'pending_settlements_total': pending_settlements_total,
            'specialty_data': specialty_data,
            'top_events': top_events,
            'recent_transactions': recent_transactions,
            'recent_doctors': recent_doctors,
            'top_vendors': top_vendors,
        })"""

new_context_block = """        # 30-day consumption chart calculation
        chart_labels = []
        chart_data = []
        last_30_days = now - timedelta(days=30)
        current = last_30_days
        while current <= now:
            next_day = current + timedelta(days=1)
            day_total = Transaction.objects.filter(transaction_date__gte=current, transaction_date__lt=next_day).aggregate(total=Sum('amount_spent'))['total'] or Decimal('0.00')
            chart_labels.append(current.strftime('%d %b'))
            chart_data.append(float(day_total))
            current = next_day

        context.update({
            'total_revenue': total_revenue,
            'total_fees': total_fees,
            'revenue_growth': round(float(revenue_growth), 1),
            'active_vouchers_count': active_vouchers_count,
            'exhausted_vouchers_count': exhausted_vouchers_count,
            'expired_vouchers_count': expired_vouchers_count,
            'total_doctors': total_doctors,
            'total_vendors': total_vendors,
            'total_transactions': total_transactions,
            'pending_settlements_total': pending_settlements_total,
            'specialty_data': specialty_data,
            'top_events': top_events,
            'recent_transactions': recent_transactions,
            'recent_doctors': recent_doctors,
            'top_vendors': top_vendors,
            'chart_labels': chart_labels,
            'chart_data': chart_data,
        })"""

views_content = views_content.replace(old_context_block, new_context_block)

with open(view_path, "w", encoding="utf-8") as f:
    f.write(views_content)
print("Updated core/views.py with chart calculations.")

# 2. Update templates/custom_admin/manager_dashboard.html
with open(template_path, "r", encoding="utf-8") as f:
    template_content = f.read()

old_fetch_js = """        // Fetch Data from API
        fetch("{% url 'dashboard_stats_api' %}")
            .then(res => res.json())
            .then(data => {
                renderSalesChart(data.chart.labels, data.chart.data);
            });"""

new_fetch_js = """        // Server-side chart data injected directly into JS
        const chartLabels = [{% for label in chart_labels %}"{{ label }}",{% endfor %}];
        const chartData = [{% for val in chart_data %}{{ val }},{% endfor %}];
        renderSalesChart(chartLabels, chartData);"""

template_content = template_content.replace(old_fetch_js, new_fetch_js)

with open(template_path, "w", encoding="utf-8") as f:
    f.write(template_content)
print("Updated manager_dashboard.html template successfully.")
