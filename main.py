import tkinter as tk
from tkinter import ttk
import pygame
import os
from pydub import AudioSegment
import threading
import time
import json
import random

class TtrpgDmBoard:
    def __init__(self, master):
        self.master = master
        master.title("D&D Soundboard")

        pygame.mixer.init()
        
        self.ambient_channel = pygame.mixer.Channel(0)
        self.effect_channel = pygame.mixer.Channel(1)
        
        self.fade_duration = 3  # Default fade duration in seconds
        self.current_ambient_sound = None
        self.current_ambient_name = None
        self.is_fading = False
        self.is_paused = False
        self.user_set_volume = 1.0  # Full volume by default

        self.ambient_queue = []
        self.ambient_timer = None
        self.playback_start_time = None

        self.ambient_label = tk.StringVar(value="100%")
        self.effect_label = tk.StringVar(value="100%")
        self.fade_label = tk.StringVar(value=f"{self.fade_duration} seconds")

        # Create directories if they don't exist
        os.makedirs("original_sounds", exist_ok=True)
        os.makedirs("normalized_sounds", exist_ok=True)

        self.load_sounds_config()
        self.normalize_sounds()
        self.create_ui()

    def load_sounds_config(self):
        with open('sounds_config.json', 'r') as f:
            self.sounds_config = json.load(f)

    def normalize_sounds(self):
        target_dBFS = -20.0
        all_sounds = (
            [sound for sounds in self.sounds_config['sound_effects'].values() for sound in sounds] +
            [sound for sounds in self.sounds_config['ambient_sounds'].values() for sound in sounds]
        )
        for sound_file in all_sounds:
            original_path = os.path.join("original_sounds", sound_file)
            normalized_path = os.path.join("normalized_sounds", f"normalized_{sound_file}")
            if os.path.exists(original_path) and not os.path.exists(normalized_path):
                sound = AudioSegment.from_file(original_path, format="mp3")
                change_in_dBFS = target_dBFS - sound.dBFS
                normalized_sound = sound.apply_gain(change_in_dBFS)
                normalized_sound.export(normalized_path, format="mp3")

    def create_ui(self):
        # Create frames
        effect_frame = ttk.LabelFrame(self.master, text="Sound Effects")
        effect_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        ambient_frame = ttk.LabelFrame(self.master, text="Ambient Sounds")
        ambient_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        control_frame = ttk.Frame(self.master)
        control_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        queue_frame = ttk.LabelFrame(self.master, text="Queued Ambient Sounds")
        queue_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=10, sticky="nsew")

        # Create buttons for sound effects
        for i, (effect_name, sound_files) in enumerate(self.sounds_config['sound_effects'].items()):
            button = tk.Button(effect_frame, text=effect_name, 
                               command=lambda e=effect_name: self.play_effect(e),
                               width=15, height=2, bg="#3498db", fg="white")
            button.grid(row=i, column=0, padx=5, pady=5)

        # Create buttons for ambient sounds
        for i, (ambient_name, sound_files) in enumerate(self.sounds_config['ambient_sounds'].items()):
            play_button = tk.Button(ambient_frame, text=f"Play {ambient_name}", 
                                    command=lambda n=ambient_name: self.play_ambient(n),
                                    width=15, height=2, bg="#4CAF50", fg="white")
            play_button.grid(row=i, column=0, padx=5, pady=5)

            fade_in_button = tk.Button(ambient_frame, text=f"Fade In {ambient_name}", 
                                       command=lambda n=ambient_name: self.fade_in_ambient(n),
                                       width=15, height=2, bg="#8e44ad", fg="white")
            fade_in_button.grid(row=i, column=1, padx=5, pady=5)

            fade_out_button = tk.Button(ambient_frame, text=f"Fade Out {ambient_name}", 
                                        command=lambda n=ambient_name: self.fade_out_ambient(n),
                                        width=15, height=2, bg="#8e44ad", fg="white")
            fade_out_button.grid(row=i, column=2, padx=5, pady=5)

            queue_button = tk.Button(ambient_frame, text=f"Queue {ambient_name}", 
                                     command=lambda n=ambient_name: self.queue_ambient(n),
                                     width=15, height=2, bg="#f39c12", fg="white")
            queue_button.grid(row=i, column=3, padx=5, pady=5)

        stop_button = tk.Button(ambient_frame, text="Stop Ambient", 
                                command=self.stop_ambient,
                                width=15, height=2, bg="#e74c3c", fg="white")
        stop_button.grid(row=len(self.sounds_config['ambient_sounds']), column=0, columnspan=4, padx=5, pady=5)

        # Create volume sliders
        self.create_volume_sliders(control_frame)
        self.create_fade_controls(control_frame)

        # Create queue list
        self.queue_listbox = tk.Listbox(queue_frame, width=30, height=10)
        self.queue_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.queue_listbox.config(yscrollcommand=scrollbar.set)

        clear_queue_button = tk.Button(queue_frame, text="Clear Queue", 
                                       command=self.clear_queue,
                                       width=15, height=2, bg="#e74c3c", fg="white")
        clear_queue_button.pack(padx=5, pady=5)

        # Add Pause/Resume and Next Song buttons
        self.pause_resume_button = tk.Button(control_frame, text="Pause", 
                                             command=self.toggle_pause_resume,
                                             width=15, height=2, bg="#3498db", fg="white")
        self.pause_resume_button.grid(row=2, column=0, padx=5, pady=5)

        next_song_button = tk.Button(control_frame, text="Next Song", 
                                     command=self.skip_to_next_song,
                                     width=15, height=2, bg="#2ecc71", fg="white")
        next_song_button.grid(row=2, column=1, padx=5, pady=5)

    def create_volume_sliders(self, parent):
        ambient_frame = ttk.LabelFrame(parent, text="Ambient Volume")
        ambient_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.ambient_slider = ttk.Scale(ambient_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                        command=self.set_ambient_volume, length=200)
        self.ambient_slider.set(100)  # Set default to max volume
        self.ambient_slider.pack(expand=True)
        tk.Label(ambient_frame, textvariable=self.ambient_label).pack()

        effect_frame = ttk.LabelFrame(parent, text="Effect Volume")
        effect_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.effect_slider = ttk.Scale(effect_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                       command=self.set_effect_volume, length=200)
        self.effect_slider.set(100)  # Set default to max volume
        self.effect_slider.pack(expand=True)
        tk.Label(effect_frame, textvariable=self.effect_label).pack()

    def create_fade_controls(self, parent):
        fade_frame = ttk.LabelFrame(parent, text="Fade Duration")
        fade_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.fade_slider = ttk.Scale(fade_frame, from_=1, to=10, orient=tk.HORIZONTAL, 
                                     command=self.set_fade_duration, length=300)
        self.fade_slider.set(self.fade_duration)
        self.fade_slider.pack(expand=True)
        tk.Label(fade_frame, textvariable=self.fade_label).pack()

    def set_ambient_volume(self, volume):
        self.user_set_volume = float(volume) / 100
        self.ambient_channel.set_volume(self.user_set_volume)
        self.ambient_label.set(f"{int(float(volume))}%")

    def set_effect_volume(self, volume):
        volume_float = float(volume) / 100
        self.effect_channel.set_volume(volume_float)
        self.effect_label.set(f"{int(float(volume))}%")

    def set_fade_duration(self, duration):
        self.fade_duration = float(duration)
        self.fade_label.set(f"{self.fade_duration:.1f} seconds")

    def play_effect(self, effect_name):
        sound_files = self.sounds_config['sound_effects'][effect_name]
        chosen_sound = random.choice(sound_files)
        sound_path = os.path.join("normalized_sounds", f"normalized_{chosen_sound}")
        if os.path.exists(sound_path):
            sound = pygame.mixer.Sound(sound_path)
            self.effect_channel.play(sound)
        else:
            print(f"Sound file not found: {sound_path}")

    def play_ambient(self, ambient_name):
        sound_files = self.sounds_config['ambient_sounds'][ambient_name]
        chosen_sound = random.choice(sound_files)
        sound_path = os.path.join("normalized_sounds", f"normalized_{chosen_sound}")
        if os.path.exists(sound_path):
            sound = pygame.mixer.Sound(sound_path)
            self.ambient_channel.stop()
            self.ambient_channel.play(sound, loops=-1)
            self.ambient_channel.set_volume(self.user_set_volume)
            self.current_ambient_sound = sound
            self.current_ambient_name = ambient_name
            self.playback_start_time = time.time()
            self.is_paused = False
            self.pause_resume_button.config(text="Pause")
            self.schedule_next_song()
        else:
            print(f"Sound file not found: {sound_path}")

    def queue_ambient(self, ambient_name):
        self.ambient_queue.append(ambient_name)
        self.update_queue_listbox()
        if not self.current_ambient_sound:
            self.play_next_in_queue()
        elif len(self.ambient_queue) == 1:
            self.schedule_next_song()

    def update_queue_listbox(self):
        self.queue_listbox.delete(0, tk.END)
        for ambient_name in self.ambient_queue:
            self.queue_listbox.insert(tk.END, ambient_name)

    def schedule_next_song(self):
        if self.ambient_timer:
            self.master.after_cancel(self.ambient_timer)
        if self.current_ambient_sound and not self.is_paused:
            remaining_time = self.get_remaining_time()
            self.ambient_timer = self.master.after(int(remaining_time * 1000), self.transition_to_next_song)

    def get_remaining_time(self):
        if self.current_ambient_sound and self.playback_start_time:
            elapsed_time = time.time() - self.playback_start_time
            total_length = self.current_ambient_sound.get_length()
            return total_length - (elapsed_time % total_length)
        return 0

    def transition_to_next_song(self):
        if self.ambient_queue:
            self.play_next_in_queue()
        else:
            self.schedule_next_song()

    def play_next_in_queue(self):
        if self.ambient_queue:
            next_ambient = self.ambient_queue.pop(0)
            self.update_queue_listbox()
            self.play_ambient(next_ambient)
        else:
            self.current_ambient_sound = None
            self.current_ambient_name = None
            self.ambient_timer = None

    def fade_in_ambient(self, ambient_name):
        sound_files = self.sounds_config['ambient_sounds'][ambient_name]
        chosen_sound = random.choice(sound_files)
        sound_path = os.path.join("normalized_sounds", f"normalized_{chosen_sound}")
        if os.path.exists(sound_path):
            sound = pygame.mixer.Sound(sound_path)
            self.current_ambient_sound = sound
            self.current_ambient_name = ambient_name
            self.is_paused = False
            self.pause_resume_button.config(text="Pause")
            threading.Thread(target=self._fade_in, args=(sound,)).start()
        else:
            print(f"Sound file not found: {sound_path}")

    def _fade_in(self, sound):
        if self.is_fading:
            return
        self.is_fading = True
        self.ambient_channel.stop()
        self.ambient_channel.play(sound, loops=-1)
        self.playback_start_time = time.time()
        steps = 100
        for step in range(steps + 1):
            volume = (step / steps) * self.user_set_volume
            self.ambient_channel.set_volume(volume)
            time.sleep(self.fade_duration / steps)
        self.is_fading = False
        self.schedule_next_song()

    def fade_out_ambient(self, ambient_name=None):
        if self.current_ambient_sound:
            threading.Thread(target=self._fade_out).start()

    def _fade_out(self):
        if self.is_fading:
            return
        self.is_fading = True
        steps = 100
        start_vol = self.ambient_channel.get_volume()
        for step in range(steps + 1):
            volume = start_vol * (1 - step / steps)
            self.ambient_channel.set_volume(volume)
            time.sleep(self.fade_duration / steps)
        self.ambient_channel.stop()
        self.ambient_channel.set_volume(self.user_set_volume)  # Reset to user-set volume
        self.current_ambient_sound = None
        self.current_ambient_name = None
        self.is_fading = False
        self.play_next_in_queue()

    def stop_ambient(self):
        self.ambient_channel.stop()
        self.ambient_channel.set_volume(self.user_set_volume)  # Reset to user-set volume
        self.current_ambient_sound = None
        self.current_ambient_name = None
        if self.ambient_timer:
            self.master.after_cancel(self.ambient_timer)
            self.ambient_timer = None
        self.clear_queue()
        self.is_paused = False
        self.pause_resume_button.config(text="Pause")

    def clear_queue(self):
        self.ambient_queue.clear()
        self.update_queue_listbox()
        if self.ambient_timer:
            self.master.after_cancel(self.ambient_timer)
            self.ambient_timer = None

    def toggle_pause_resume(self):
        if self.ambient_channel.get_busy():
            if self.is_paused:
                self.ambient_channel.unpause()
                self.is_paused = False
                self.pause_resume_button.config(text="Pause")
                # Adjust playback_start_time when unpausing
                self.playback_start_time = time.time() - (time.time() - self.playback_start_time) % self.current_ambient_sound.get_length()
                self.schedule_next_song()
            else:
                self.ambient_channel.pause()
                self.is_paused = True
                self.pause_resume_button.config(text="Resume")
                if self.ambient_timer:
                    self.master.after_cancel(self.ambient_timer)

    def skip_to_next_song(self):
        if self.ambient_queue:
            self.is_paused = False
            self.pause_resume_button.config(text="Pause")
            self.transition_to_next_song()
        else:
            self.stop_ambient()

if __name__ == "__main__":
    root = tk.Tk()
    soundboard = TtrpgDmBoard(root)
    root.mainloop()