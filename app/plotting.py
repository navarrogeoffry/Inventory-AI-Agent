# app/plotting.py
import matplotlib
matplotlib.use('Agg') # Use Agg backend for non-interactive plotting (important for servers)
import matplotlib.pyplot as plt
import io
import logging

logger = logging.getLogger(__name__)

# --- Bar Chart Function (Unchanged) ---
def create_bar_chart(data: list[dict], x_col: str, y_col: str, title: str = "Bar Chart") -> io.BytesIO | None:
    """Generates a simple bar chart from a list of dictionaries."""
    if not data: logger.warning("No data for bar chart."); return None
    if not x_col or not y_col: logger.warning("X/Y columns needed for bar chart."); return None
    try:
        x_values = [str(item.get(x_col, 'N/A')) for item in data] # Ensure x is string for labels
        y_values = [float(item.get(y_col, 0)) for item in data] # Ensure y is float

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(x_values, y_values)
        ax.set_xlabel(x_col.replace('_', ' ').title())
        ax.set_ylabel(y_col.replace('_', ' ').title())
        ax.set_title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
        logger.info(f"Successfully generated bar chart: {title}")
        return buf
    except Exception as e: logger.error(f"Error generating bar chart: {e}"); plt.close(fig); return None

# --- Pie Chart Function (Unchanged) ---
def create_pie_chart(data: list[dict], label_col: str, value_col: str, title: str = "Pie Chart") -> io.BytesIO | None:
    """Generates a simple pie chart."""
    if not data: logger.warning("No data for pie chart."); return None
    if not label_col or not value_col: logger.warning("Label/Value columns needed for pie chart."); return None
    try:
        labels = [str(item.get(label_col, 'N/A')) for item in data]
        values = [float(item.get(value_col, 0)) for item in data]
        valid_data = [(l, v) for l, v in zip(labels, values) if v > 0]
        if not valid_data: logger.warning("No positive data for pie chart."); return None
        labels, values = zip(*valid_data)

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal'); ax.set_title(title); plt.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
        logger.info(f"Successfully generated pie chart: {title}")
        return buf
    except Exception as e: logger.error(f"Error generating pie chart: {e}"); plt.close(fig); return None

# --- NEW: Line Chart Function ---
def create_line_chart(data: list[dict], x_col: str, y_col: str, title: str = "Line Chart") -> io.BytesIO | None:
    """
    Generates a simple line chart. Assumes x_col can be sorted meaningfully.
    Best for trends if x_col represents time or sequence.
    """
    if not data: logger.warning("No data for line chart."); return None
    if not x_col or not y_col: logger.warning("X/Y columns needed for line chart."); return None
    try:
        # Attempt to convert x and y values, assuming they can be numeric or sorted
        # More robust handling might be needed depending on actual data types
        plot_data = []
        for item in data:
            try:
                x_val = item.get(x_col)
                y_val = float(item.get(y_col, 0)) # Y must be numeric
                plot_data.append({'x': x_val, 'y': y_val})
            except (ValueError, TypeError):
                logger.warning(f"Skipping row due to conversion error for line chart: {item}")
                continue

        if not plot_data:
            logger.warning("No valid numeric data points found for line chart.")
            return None

        # Sort data based on x_values for a meaningful line plot
        # This assumes x_values are sortable (e.g., numbers, dates, or ordered strings)
        try:
            plot_data.sort(key=lambda item: item['x'])
        except TypeError:
            logger.warning(f"Cannot sort x-values ('{x_col}') for line chart, plot might be misleading.")
            # Proceed without sorting if sorting fails

        x_values = [item['x'] for item in plot_data]
        y_values = [item['y'] for item in plot_data]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(x_values, y_values, marker='o') # Plot with markers
        ax.set_xlabel(x_col.replace('_', ' ').title())
        ax.set_ylabel(y_col.replace('_', ' ').title())
        ax.set_title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
        logger.info(f"Successfully generated line chart: {title}")
        return buf
    except Exception as e: logger.error(f"Error generating line chart: {e}"); plt.close(fig); return None

# --- NEW: Scatter Plot Function ---
def create_scatter_plot(data: list[dict], x_col: str, y_col: str, title: str = "Scatter Plot") -> io.BytesIO | None:
    """
    Generates a simple scatter plot. Requires both x_col and y_col to be numeric.
    """
    if not data: logger.warning("No data for scatter plot."); return None
    if not x_col or not y_col: logger.warning("X/Y columns needed for scatter plot."); return None
    try:
        x_values = []
        y_values = []
        # Ensure both columns are numeric
        for item in data:
            try:
                x_val = float(item.get(x_col))
                y_val = float(item.get(y_col))
                x_values.append(x_val)
                y_values.append(y_val)
            except (ValueError, TypeError, AttributeError):
                logger.warning(f"Skipping row with non-numeric data for scatter plot: {item}")
                continue # Skip rows where conversion fails

        if not x_values: # Check if any valid data points remain
             logger.warning("No valid numeric data points found for scatter plot.")
             return None

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.scatter(x_values, y_values)
        ax.set_xlabel(x_col.replace('_', ' ').title())
        ax.set_ylabel(y_col.replace('_', ' ').title())
        ax.set_title(title)
        plt.grid(True) # Add grid for better readability
        plt.tight_layout()
        buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(fig); buf.seek(0)
        logger.info(f"Successfully generated scatter plot: {title}")
        return buf
    except Exception as e: logger.error(f"Error generating scatter plot: {e}"); plt.close(fig); return None

