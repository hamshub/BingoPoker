/**
 * api.js - BingoPoker API communication layer
 * 
 * Handles all REST API calls to the backend
 */

// Switch to full URL with port when deploying to shared hosting
const API_BASE = '/api';

class BingoPokerAPI {
    /**
     * Register or get user
     */
    static async registerUser(email, username, role = 'worker') {
        try {
            const response = await fetch(`${API_BASE}/user`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, username, role })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Registration failed');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Register user error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get user profile
     */
    static async getUser(email) {
        try {
            const response = await fetch(`${API_BASE}/user/${encodeURIComponent(email)}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'User not found');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Get user error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Update user role
     */
    static async updateRole(email, newRole) {
        try {
            const response = await fetch(`${API_BASE}/user/${encodeURIComponent(email)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ role: newRole })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Update failed');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Update role error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Create a new room
     */
    static async createRoom(name, grid, createdBy) {
        try {
            const response = await fetch(`${API_BASE}/room`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    grid,
                    created_by: createdBy
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Room creation failed');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Create room error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get room state
     */
    static async getRoom(roomId) {
        try {
            const response = await fetch(`${API_BASE}/room/${roomId}`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Room not found');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Get room error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * List all active rooms
     */
    static async listRooms() {
        try {
            const response = await fetch(`${API_BASE}/rooms`);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Failed to load rooms');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('List rooms error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Delete a room
     */
    static async deleteRoom(roomId, createdBy) {
        try {
            const response = await fetch(`${API_BASE}/room/${roomId}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ created_by: createdBy })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || 'Delete failed');
            }
            
            return { success: true, data };
        } catch (error) {
            console.error('Delete room error:', error);
            return { success: false, error: error.message };
        }
    }
}

/**
 * Grid utility functions
 */

const GridUtils = {
    /**
     * Default bingo grid
     */
    DEFAULT_GRID: [
        ["New feature",             "Rework",                "Core modification",            "UI modification",          "Database Queries"],
        ["API modification",        "Country specific",      "Migration needed",             "Merge needed",             "Refactor needed"],
        ["Inadequate specification","Inadequate documentation","¯\\_(ツ)_/¯",              "Cross-team collaboration", "Complex task"],
        ["New unit tests",          "Rewrite unit tests",    "New test cases",               "Sandbox test required",    "Not testable locally"],
        ["Outside domain area",     "Monetary operation",    "External component dependency","Nuget update needed",      "No test data available"]
    ],

    /**
     * Empty grid template
     */
    createEmptyGrid() {
        return Array(5).fill(null).map(() => Array(5).fill(""));
    },

    /**
     * Identify the center cell (2,2) — styled differently, but not otherwise special
     */
    isCenterCell(row, col) {
        return row === 2 && col === 2;
    },

    /**
     * Validate grid is 5x5
     */
    isValidGrid(grid) {
        if (!Array.isArray(grid) || grid.length !== 5) return false;
        return grid.every(row => Array.isArray(row) && row.length === 5);
    }
};

