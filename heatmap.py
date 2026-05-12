import os
import pandas as pd
import plotly.express as px
import pycountry
import numpy as np

def generate_world_map():
    # Define the output directory
    output_dir = "./outputs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    data = []
    
    # Get all .txt files in the current directory where the script sits
    files = [f for f in os.listdir('.') if f.endswith('.txt')]
    
    print(f"Processing {len(files)} files found in current directory...")

    for filename in files:
        # Extract potential ccTLD (e.g., 'gb' from 'gb.txt')
        code = filename.replace(".txt", "").strip().upper()
        
        # Check if it's a valid 2-letter ISO country code
        country = pycountry.countries.get(alpha_2=code)
        
        if country:
            try:
                # Open file and count lines
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    count = sum(1 for line in f if line.strip())
                
                if count > 0:
                    data.append({
                        'Country': country.name,
                        'ISO3': country.alpha_3,
                        'Count': count
                    })
            except Exception as e:
                print(f"Error reading {filename}: {e}")
        # If no match is found (e.g., LICENSE.txt, commonwealth.txt), it is ignored

    if not data:
        print("No valid country data found. Ensure your .txt files are in the same folder as this script.")
        return

    df = pd.DataFrame(data)

    # Use Log Scale for better color distribution across wide ranges
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
            projection_type='natural earth'
        ),
        margin={"r":0,"t":50,"l":0,"b":0}
    )

    # Save to the ./outputs folder
    output_path = os.path.join(output_dir, "domain_heatmap.html")
    fig.write_html(output_path)
    
    print("-" * 30)
    print(f"Success! Map saved to: {output_path}")
    print("-" * 30)
    
    # Attempt to open in browser automatically
    fig.show()

if __name__ == "__main__":
    generate_world_map()