'''enumerate_sum9.py

Utility script to enumerate all combinations (with repetition) of the allowed digits
{1,2,4,5,7,8} that sum to 9. It also prints the corresponding product multiplied by 11
for each combination, illustrating the relationship discussed (sum=9 ↔ 11×product).

The script is meant as a companion to the cyclic compression project and can be
run directly:
    python -m tools.enumerate_sum9
'''

from itertools import combinations_with_replacement

def main():
    allowed = [1, 2, 4, 5, 7, 8]
    combos = []
    for combo in combinations_with_replacement(allowed, 3):
        if sum(combo) == 9:
            combos.append(combo)
    if not combos:
        print("No combinations sum to 9.")
        return
    print(f"Found {len(combos)} combination(s) whose sum is 9 (order-independent, repeats allowed):")
    for combo in combos:
        product = combo[0] * combo[1] * combo[2]
        eleven_product = product * 11
        print(f"  {combo} -> sum=9, product={product}, 11*product={eleven_product}")

if __name__ == "__main__":
    main()
