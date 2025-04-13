import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys

# Check if at least one filename was provided
if len(sys.argv) < 2:
    print("Usage: python plot.py piggyback.csv [stopandwait.csv]")
    print("Note: stopandwait.csv is optional for comparison")
    sys.exit(1)

# Determine if we're doing comparative analysis or single protocol analysis
do_comparison = len(sys.argv) >= 3
piggyback_file = sys.argv[1]
stopandwait_file = sys.argv[2] if do_comparison else None

# Load the CSV files with results
try:
    piggyback_df = pd.read_csv(piggyback_file)
    if do_comparison:
        stopandwait_df = pd.read_csv(stopandwait_file)
        print(f"Comparing piggybacking protocol with stop-and-wait protocol")
    else:
        print(f"Analyzing piggybacking protocol only")
except Exception as e:
    print(f"Error loading CSV files: {e}")
    sys.exit(1)


# Extract relevant metrics
def extract_metrics(df):
    # Key metrics to compare
    messages_sent = df['transmitted_frames'].iloc[0]
    messages_received = df['successful_applications'].iloc[0]
    execution_time = df['execution_time'].iloc[0] / 1_000_000  # Convert to seconds
    avg_latency = df['average_application_latency'].iloc[0] / 1_000  # Convert to milliseconds

    # Calculate throughput (messages per second)
    throughput = messages_received / execution_time

    # Calculate efficiency (success rate)
    efficiency = messages_received / messages_sent if messages_sent > 0 else 0

    return {
        'messages_sent': messages_sent,
        'messages_received': messages_received,
        'execution_time': execution_time,
        'avg_latency': avg_latency,
        'throughput': throughput,
        'efficiency': efficiency
    }


pg_metrics = extract_metrics(piggyback_df)
if do_comparison:
    sw_metrics = extract_metrics(stopandwait_df)

# Create visualizations
if do_comparison:
    # Create a figure with subplots for comparison
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    plt.subplots_adjust(hspace=0.3)

    # Plot 1: Messages Sent vs Received
    labels = ['Stop-and-Wait', 'Piggybacking']
    x = np.arange(len(labels))
    width = 0.35

    axes[0, 0].bar(x - width / 2, [sw_metrics['messages_sent'], pg_metrics['messages_sent']],
                   width, label='Transmitted')
    axes[0, 0].bar(x + width / 2, [sw_metrics['messages_received'], pg_metrics['messages_received']],
                   width, label='Received')
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(labels)
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].set_title('Messages Transmitted vs Received')
    axes[0, 0].legend()

    # Plot 2: Throughput (messages per second)
    throughputs = [sw_metrics['throughput'], pg_metrics['throughput']]
    axes[0, 1].bar(labels, throughputs, color=['steelblue', 'darkorange'])
    axes[0, 1].set_ylabel('Messages per second')
    axes[0, 1].set_title('Throughput')

    # Add percentage improvement
    pg_improvement = ((pg_metrics['throughput'] / sw_metrics['throughput']) - 1) * 100
    axes[0, 1].text(1, pg_metrics['throughput'] * 1.05,
                    f"+{pg_improvement:.1f}%",
                    ha='center',
                    fontweight='bold')

    # Plot 3: Average Latency
    latencies = [sw_metrics['avg_latency'], pg_metrics['avg_latency']]
    axes[1, 0].bar(labels, latencies, color=['steelblue', 'darkorange'])
    axes[1, 0].set_ylabel('Milliseconds')
    axes[1, 0].set_title('Average Message Latency')

    # Add percentage improvement (lower is better)
    latency_improvement = ((sw_metrics['avg_latency'] / pg_metrics['avg_latency']) - 1) * 100
    if latency_improvement > 0:
        improvement_text = f"-{latency_improvement:.1f}%"
    else:
        improvement_text = f"+{-latency_improvement:.1f}%"
    axes[1, 0].text(1, pg_metrics['avg_latency'] * 1.05,
                    improvement_text,
                    ha='center',
                    fontweight='bold')

    # Plot 4: Efficiency (successful messages / total transmitted)
    efficiencies = [sw_metrics['efficiency'] * 100, pg_metrics['efficiency'] * 100]  # Convert to percentage
    axes[1, 1].bar(labels, efficiencies, color=['steelblue', 'darkorange'])
    axes[1, 1].set_ylabel('Percentage (%)')
    axes[1, 1].set_title('Protocol Efficiency')
    axes[1, 1].set_ylim([0, 100])

    # Add percentage improvement
    eff_improvement = ((pg_metrics['efficiency'] / sw_metrics['efficiency']) - 1) * 100
    axes[1, 1].text(1, pg_metrics['efficiency'] * 100 * 1.05,
                    f"+{eff_improvement:.1f}%",
                    ha='center',
                    fontweight='bold')

    # Add a title to the entire figure
    plt.suptitle('Stop-and-Wait vs. Piggybacking Protocol Performance', fontsize=16)

    # Add a text summary at the bottom
    summary_text = (
        f"Summary:\n"
        f"- Stop-and-Wait: {sw_metrics['messages_received']} messages received, "
        f"{sw_metrics['throughput']:.2f} msgs/sec, {sw_metrics['avg_latency']:.2f} ms latency\n"
        f"- Piggybacking: {pg_metrics['messages_received']} messages received, "
        f"{pg_metrics['throughput']:.2f} msgs/sec, {pg_metrics['avg_latency']:.2f} ms latency"
    )
    fig.text(0.5, 0.01, summary_text, ha='center', fontsize=10)

    # Save the figure
    plt.savefig('protocol_comparison.png', dpi=300, bbox_inches='tight')
    print(f"Plot saved as 'protocol_comparison.png'")

    # Print detailed statistics to console
    print("\n----- Detailed Statistics -----")
    print("\nStop-and-Wait Protocol:")
    print(f"  Messages Transmitted: {sw_metrics['messages_sent']}")
    print(f"  Messages Received: {sw_metrics['messages_received']}")
    print(f"  Throughput: {sw_metrics['throughput']:.2f} messages/second")
    print(f"  Average Latency: {sw_metrics['avg_latency']:.2f} ms")
    print(f"  Efficiency: {sw_metrics['efficiency'] * 100:.2f}%")

    print("\nPiggybacking Protocol:")
    print(f"  Messages Transmitted: {pg_metrics['messages_sent']}")
    print(f"  Messages Received: {pg_metrics['messages_received']}")
    print(f"  Throughput: {pg_metrics['throughput']:.2f} messages/second")
    print(f"  Average Latency: {pg_metrics['avg_latency']:.2f} ms")
    print(f"  Efficiency: {pg_metrics['efficiency'] * 100:.2f}%")

    print("\nPerformance Improvement with Piggybacking:")
    print(f"  Throughput: {pg_improvement:.2f}%")
    print(f"  Latency: {latency_improvement:.2f}% ({'better' if latency_improvement > 0 else 'worse'})")
    print(f"  Efficiency: {eff_improvement:.2f}%")

else:
    # Single protocol analysis - create a figure with metrics for just piggybacking
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    plt.subplots_adjust(hspace=0.3)

    # Plot 1: Messages Sent vs Received
    axes[0, 0].bar(['Transmitted', 'Received'],
                   [pg_metrics['messages_sent'], pg_metrics['messages_received']],
                   color=['steelblue', 'darkorange'])
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].set_title('Messages Transmitted vs Received')

    # Plot 2: Throughput
    axes[0, 1].bar(['Piggybacking'], [pg_metrics['throughput']], color='darkorange')
    axes[0, 1].set_ylabel('Messages per second')
    axes[0, 1].set_title('Throughput')

    # Plot 3: Average Latency
    axes[1, 0].bar(['Piggybacking'], [pg_metrics['avg_latency']], color='darkorange')
    axes[1, 0].set_ylabel('Milliseconds')
    axes[1, 0].set_title('Average Message Latency')

    # Plot 4: Efficiency
    axes[1, 1].bar(['Piggybacking'], [pg_metrics['efficiency'] * 100], color='darkorange')
    axes[1, 1].set_ylabel('Percentage (%)')
    axes[1, 1].set_title('Protocol Efficiency')
    axes[1, 1].set_ylim([0, 100])

    # Add a title to the entire figure
    plt.suptitle('Piggybacking Protocol Performance', fontsize=16)

    # Add a text summary at the bottom
    summary_text = (
        f"Summary:\n"
        f"- Piggybacking: {pg_metrics['messages_received']} messages received, "
        f"{pg_metrics['throughput']:.2f} msgs/sec, {pg_metrics['avg_latency']:.2f} ms latency, "
        f"{pg_metrics['efficiency'] * 100:.2f}% efficiency"
    )
    fig.text(0.5, 0.01, summary_text, ha='center', fontsize=10)

    # Save the figure
    plt.savefig('piggyback_analysis.png', dpi=300, bbox_inches='tight')
    print(f"Plot saved as 'piggyback_analysis.png'")

    # Print detailed statistics to console
    print("\n----- Piggybacking Protocol Statistics -----")
    print(f"  Messages Transmitted: {pg_metrics['messages_sent']}")
    print(f"  Messages Received: {pg_metrics['messages_received']}")
    print(f"  Execution Time: {pg_metrics['execution_time']:.2f} seconds")
    print(f"  Throughput: {pg_metrics['throughput']:.2f} messages/second")
    print(f"  Average Latency: {pg_metrics['avg_latency']:.2f} ms")
    print(f"  Efficiency: {pg_metrics['efficiency'] * 100:.2f}%")

# Print recommendations for testing different network conditions
print("\nRecommendations for further testing:")
print("To determine the optimal conditions for piggybacking, try varying:")
print("1. Message Rate: Test with values from 100ms to 5000ms")
print("2. Bandwidth: Compare low (9.6Kbps) vs high (1Mbps)")
print("3. Propagation Delay: Test from 10ms to 5000ms")
print("4. Frame Corruption Rate: Vary from 0% to 10%")
print("\nPiggybacking typically performs best with:")
print("- Bidirectional traffic (both nodes sending data)")
print("- Medium to high propagation delays")
print("- Limited bandwidth")
print("- Low to moderate error rates")