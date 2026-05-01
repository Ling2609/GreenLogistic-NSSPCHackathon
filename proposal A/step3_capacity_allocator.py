import pandas as pd

print("========================================")
print(" STEP 3: THE CAPACITY ALLOCATOR")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD THE MATCHES FROM STEP 2
# ---------------------------------------------------------
print("1. Loading possible matches...")
df_matches = pd.read_excel("Step2_All_Possible_Matches.xlsx")

# ---------------------------------------------------------
# 2. SET UP OUR TRACKERS (The Inventory & Shopping Lists)
# ---------------------------------------------------------
print("2. Setting up inventory and demand trackers...")

# Create a dictionary of every Farm's starting inventory for each vegetable
# Format: {(farm_id, sku_id): 2000}
farm_inventory = df_matches.groupby(['farm_id', 'sku_id'])['daily_capacity_boxes'].first().to_dict()

# Create a dictionary of every Customer's shopping list
# Format: {(customer_id, sku_id): 150}
customer_demand = df_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes'].first().to_dict()

# ---------------------------------------------------------
# 3. THE ALLOCATION ENGINE
# ---------------------------------------------------------
print("3. Allocating orders based on closest distance and available capacity...")

final_allocations = []

# Because Step 2 already sorted this by shortest distance, 
# iterating through it row-by-row guarantees we always try the closest farm first!
for index, row in df_matches.iterrows():
    cust = row['customer_id']
    sku = row['sku_id']
    farm = row['farm_id']
    
    # Check how many boxes the customer still needs
    boxes_needed = customer_demand.get((cust, sku), 0)
    
    # Check how many boxes the farm still has
    boxes_available = farm_inventory.get((farm, sku), 0)
    
    # If the customer is fully satisfied OR the farm is totally empty, skip to the next option
    if boxes_needed <= 0 or boxes_available <= 0:
        continue
        
    # Figure out how many boxes we can actually move (The smaller of the two numbers)
    boxes_to_move = min(boxes_needed, boxes_available)
    
    # -------------------
    # MAKE THE TRANSACTION
    # -------------------
    # 1. Update the trackers
    customer_demand[(cust, sku)] -= boxes_to_move
    farm_inventory[(farm, sku)] -= boxes_to_move
    
    # 2. Record the receipt
    allocation_record = row.copy()
    allocation_record['allocated_boxes'] = boxes_to_move
    final_allocations.append(allocation_record)

# ---------------------------------------------------------
# 4. VERIFY AND EXPORT
# ---------------------------------------------------------
df_final = pd.DataFrame(final_allocations)

# Let's do a strict mathematical check to ensure no rules were broken
print("\n--- VERIFICATION CHECKS ---")

total_demand_originally = sum(df_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes'].first())
total_boxes_allocated = df_final['allocated_boxes'].sum()

print(f"Total Boxes Demanded:  {total_demand_originally}")
print(f"Total Boxes Allocated: {total_boxes_allocated}")

if total_demand_originally == total_boxes_allocated:
    print("SUCCESS: 100% of customer orders were fulfilled!")
else:
    print("ERROR: Some customers did not get their vegetables!")

# Check if any farm breached capacity
breaches = 0
for (farm, sku), used_boxes in df_final.groupby(['farm_id', 'sku_id'])['allocated_boxes'].sum().items():
    limit = df_matches[(df_matches['farm_id'] == farm) & (df_matches['sku_id'] == sku)]['daily_capacity_boxes'].iloc[0]
    if used_boxes > limit:
        print(f"ERROR: {farm} sold {used_boxes} {sku}, but only had {limit}!")
        breaches += 1

if breaches == 0:
    print("SUCCESS: No farm capacity limits were breached!")

print("========================================\n")

# Save our mathematically perfect Fulfillment Plan!
df_final.to_excel("Step3_Final_Fulfillment_Plan.xlsx", index=False)
print("Saved bulletproof allocation to 'Step3_Final_Fulfillment_Plan.xlsx'")