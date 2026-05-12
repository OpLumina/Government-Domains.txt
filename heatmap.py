import os
import pandas as pd
import plotly.express as px
import pycountry
import numpy as np

def generate_world_map():
    # Define the directory to look for files (relative to script)
    output_dir = "./outputs"
    
    # Check if the directory exists
    if not os.path.exists(output_dir):
        print(f"Error: The directory '{output_dir}' does not exist.")
        return

    data = []
    
    # Get all .txt files inside the ./outputs directory
    files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]
    
    if not files:
        print(f"No .txt files found in {output_dir}")
        return

    print(f"Processing {len(files)} files found in {output_dir}...")

    for filename in files:
        # Get just the first 2 characters (e.g., 'us' from 'us-part-1.txt')
        code = filename[:2].upper()
        
        # Check if it's a valid 2-letter ISO country code
        country = pycountry.countries.get(alpha_2=code)
        
        if country:
            filepath = os.path.join(output_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    count = sum(1 for line in f if line.strip())
                
                if count > 0:
                    # Check if we already have an entry for this country in our list
                    existing_entry = next((item for item in data if item["ISO3"] == country.alpha_3), None)
                    
                    if existing_entry:
                        # Add to the existing total
                        existing_entry['Count'] += count
                    else:
                        # Create a new entry
                        data.append({
                            'Country': country.name,
                            'ISO3': country.alpha_3,
                            'Count': count
                        })
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    if not data:
        print(f"No valid country data found. Ensure your .txt files (named like 'us.txt') are in '{output_dir}'.")
        return

    df = pd.DataFrame(data)

    # Use Log Scale for better color distribution
    df['DisplayCount'] = np.log10(df['Count'])

    # Create the Map
    fig = px.choropleth(
        df,
        locations="ISO3",
        color="DisplayCount", 
        hover_name="Country",
        hover_data={"ISO3": False, "DisplayCount": False, "Count": True},
        color_continuous_scale=px.colors.sequential.Plasma,
        title="Global Domain Distribution Heat Map",
        labels={'DisplayCount': 'Scale (Log10)', 'Count': 'Total Domains'}
    )

    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth',
            bgcolor='rgba(0,0,0,0)' # Transparent background
        ),
        margin={"r":0,"t":50,"l":0,"b":0}
    )

    # Save to PNG
    output_path = os.path.join(output_dir, "domain_heatmap.png")
    
    print("Generating PNG image... (this may take a moment)")
    
    # We specify the engine as kaleido and set a high resolution (scale=2 for 2x DPI)
    fig.write_image(output_path, engine="kaleido", width=1200, height=800, scale=2)
    
    print("-" * 30)
    print(f"Success! Map saved as PNG to: {output_path}")
    print("-" * 30)

if __name__ == "__main__":
    generate_world_map()
